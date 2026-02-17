"""Reviewer job queue with repo-inclusive dedup and cooperative cancel."""

import asyncio
from collections import deque
from typing import Awaitable, Callable

from booty.logging import get_logger
from booty.reviewer.job import ReviewerJob


def _dedup_key(repo_full_name: str, pr_number: int, head_sha: str) -> str:
    return f"{repo_full_name}:{pr_number}:{head_sha}"


class ReviewerQueue:
    """Async queue for ReviewerJobs with repo-inclusive dedup and cancel support."""

    def __init__(self, maxsize: int = 100):
        self._queue: asyncio.Queue[ReviewerJob] = asyncio.Queue(maxsize=maxsize)
        self._processed: set[str] = set()
        self._processed_order: deque[str] = deque()
        self._cancel_events: dict[tuple[str, int], asyncio.Event] = {}
        self._worker_tasks: list[asyncio.Task] = []
        self._logger = get_logger()

    def is_duplicate(self, repo_full_name: str, pr_number: int, head_sha: str) -> bool:
        """Check if this repo+PR+head_sha was already processed or enqueued."""
        return _dedup_key(repo_full_name, pr_number, head_sha) in self._processed

    def mark_processed(self, repo_full_name: str, pr_number: int, head_sha: str) -> None:
        """Mark repo+PR+head_sha as processed (used before enqueue to reserve slot)."""
        key = _dedup_key(repo_full_name, pr_number, head_sha)
        self._processed.add(key)
        self._processed_order.append(key)
        if len(self._processed) > 10000:
            oldest = self._processed_order.popleft()
            self._processed.discard(oldest)

    def request_cancel(self, repo_full_name: str, pr_number: int) -> None:
        """Signal in-flight worker for same PR to cancel (best-effort)."""
        key = (repo_full_name, pr_number)
        if key in self._cancel_events:
            self._cancel_events[key].set()

    async def enqueue(self, job: ReviewerJob) -> bool:
        """Enqueue a reviewer job. Returns False if duplicate.

        On enqueue: cancels prior run for same PR, creates new cancel_event, marks processed, puts job.
        """
        repo_full_name = f"{job.owner}/{job.repo_name}"
        key = _dedup_key(repo_full_name, job.pr_number, job.head_sha)
        if key in self._processed:
            self._logger.warning(
                "reviewer_duplicate",
                job_id=job.job_id,
                repo=repo_full_name,
                pr_number=job.pr_number,
                head_sha=job.head_sha[:7],
            )
            return False

        self.request_cancel(repo_full_name, job.pr_number)
        event = asyncio.Event()
        self._cancel_events[(repo_full_name, job.pr_number)] = event
        job.cancel_event = event

        self.mark_processed(repo_full_name, job.pr_number, job.head_sha)

        try:
            await asyncio.wait_for(self._queue.put(job), timeout=1.0)
            self._logger.info(
                "reviewer_enqueued",
                job_id=job.job_id,
                pr_number=job.pr_number,
                queue_size=self._queue.qsize(),
            )
            return True
        except asyncio.TimeoutError:
            self._logger.error(
                "reviewer_enqueue_timeout",
                job_id=job.job_id,
                pr_number=job.pr_number,
            )
            self._processed.discard(key)
            self._cancel_events.pop((repo_full_name, job.pr_number), None)
            return False

    async def worker(
        self,
        worker_id: int,
        process_fn: Callable[[ReviewerJob], Awaitable[None]],
    ) -> None:
        """Worker loop that processes ReviewerJobs."""
        log = self._logger.bind(worker_id=worker_id)
        log.info("reviewer_worker_started")

        while True:
            try:
                job = await self._queue.get()
                log = log.bind(job_id=job.job_id, pr_number=job.pr_number)
                log.info("reviewer_job_started")

                repo_full_name = f"{job.owner}/{job.repo_name}"
                cancel_key = (repo_full_name, job.pr_number)

                try:
                    await process_fn(job)
                    log.info("reviewer_job_completed")
                except Exception as e:
                    log.error(
                        "reviewer_job_failed",
                        error=str(e),
                        exc_info=True,
                    )
                finally:
                    self._cancel_events.pop(cancel_key, None)
                    self._queue.task_done()
                    from booty.operator.last_run import record_agent_completed

                    record_agent_completed("reviewer")
            except asyncio.CancelledError:
                log.info("reviewer_worker_cancelled")
                break
            except Exception as e:
                log.error("reviewer_worker_error", error=str(e), exc_info=True)

    async def start_workers(
        self,
        num_workers: int,
        process_fn: Callable[[ReviewerJob], Awaitable[None]],
    ) -> None:
        """Start reviewer worker tasks."""
        self._logger.info("reviewer_workers_starting", num_workers=num_workers)
        for i in range(num_workers):
            task = asyncio.create_task(self.worker(i, process_fn))
            self._worker_tasks.append(task)

    async def shutdown(self) -> None:
        """Gracefully shutdown reviewer workers."""
        self._logger.info(
            "reviewer_workers_shutting_down",
            num_workers=len(self._worker_tasks),
        )
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
