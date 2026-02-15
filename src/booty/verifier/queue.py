"""Verifier job queue with PR-level deduplication."""

import asyncio
from collections import deque
from typing import Awaitable, Callable

from booty.logging import get_logger
from booty.verifier.job import VerifierJob


def _dedup_key(pr_number: int, head_sha: str) -> str:
    return f"{pr_number}:{head_sha}"


class VerifierQueue:
    """Async queue for VerifierJobs with PR-level deduplication."""

    def __init__(self, maxsize: int = 100):
        self._queue: asyncio.Queue[VerifierJob] = asyncio.Queue(maxsize=maxsize)
        self._processed: set[str] = set()
        self._processed_order: deque[str] = deque()
        self._worker_tasks: list[asyncio.Task] = []
        self._logger = get_logger()

    def is_duplicate(self, pr_number: int, head_sha: str) -> bool:
        """Check if this PR+head_sha was already processed or enqueued."""
        return _dedup_key(pr_number, head_sha) in self._processed

    def mark_processed(self, pr_number: int, head_sha: str) -> None:
        """Mark PR+head_sha as processed (used before enqueue to reserve slot)."""
        key = _dedup_key(pr_number, head_sha)
        self._processed.add(key)
        self._processed_order.append(key)
        if len(self._processed) > 10000:
            oldest = self._processed_order.popleft()
            self._processed.discard(oldest)

    async def enqueue(self, job: VerifierJob) -> bool:
        """Enqueue a verifier job. Returns False if duplicate."""
        key = _dedup_key(job.pr_number, job.head_sha)
        if key in self._processed:
            self._logger.warning(
                "verifier_duplicate",
                job_id=job.job_id,
                pr_number=job.pr_number,
                head_sha=job.head_sha[:7],
            )
            return False

        self.mark_processed(job.pr_number, job.head_sha)

        try:
            await asyncio.wait_for(self._queue.put(job), timeout=1.0)
            self._logger.info(
                "verifier_enqueued",
                job_id=job.job_id,
                pr_number=job.pr_number,
                queue_size=self._queue.qsize(),
            )
            return True
        except asyncio.TimeoutError:
            self._logger.error(
                "verifier_enqueue_timeout",
                job_id=job.job_id,
                pr_number=job.pr_number,
            )
            self._processed.discard(key)
            return False

    async def worker(
        self,
        worker_id: int,
        process_fn: Callable[[VerifierJob], Awaitable[None]],
    ) -> None:
        """Worker loop that processes VerifierJobs."""
        log = self._logger.bind(worker_id=worker_id)
        log.info("verifier_worker_started")

        while True:
            try:
                job = await self._queue.get()
                log = log.bind(job_id=job.job_id, pr_number=job.pr_number)
                log.info("verifier_job_started")

                try:
                    await process_fn(job)
                    log.info("verifier_job_completed")
                except Exception as e:
                    log.error(
                        "verifier_job_failed",
                        error=str(e),
                        exc_info=True,
                    )
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                log.info("verifier_worker_cancelled")
                break
            except Exception as e:
                log.error("verifier_worker_error", error=str(e), exc_info=True)

    async def start_workers(
        self,
        num_workers: int,
        process_fn: Callable[[VerifierJob], Awaitable[None]],
    ) -> None:
        """Start verifier worker tasks."""
        self._logger.info("verifier_workers_starting", num_workers=num_workers)
        for i in range(num_workers):
            task = asyncio.create_task(self.worker(i, process_fn))
            self._worker_tasks.append(task)

    async def shutdown(self) -> None:
        """Gracefully shutdown verifier workers."""
        self._logger.info(
            "verifier_workers_shutting_down",
            num_workers=len(self._worker_tasks),
        )
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
