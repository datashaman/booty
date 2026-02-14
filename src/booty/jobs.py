"""Job queue with state tracking and idempotency."""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Awaitable, Callable

from booty.logging import get_logger


class JobState(Enum):
    """Job state enumeration."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """Job data structure."""

    job_id: str
    issue_url: str
    issue_number: int
    payload: dict
    state: JobState = JobState.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None


class JobQueue:
    """Async job queue with idempotency and worker pool."""

    def __init__(self, maxsize: int = 100):
        """Initialize job queue.

        Args:
            maxsize: Maximum queue size
        """
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self.jobs: dict[str, Job] = {}
        self.processed_deliveries: set[str] = set()
        self._delivery_order: deque[str] = deque()
        self._worker_tasks: list[asyncio.Task] = []
        self._logger = get_logger()

    def is_duplicate(self, delivery_id: str) -> bool:
        """Check if delivery ID has already been processed.

        Args:
            delivery_id: GitHub webhook delivery ID

        Returns:
            True if already processed
        """
        return delivery_id in self.processed_deliveries

    def mark_processed(self, delivery_id: str) -> None:
        """Mark delivery ID as processed.

        Args:
            delivery_id: GitHub webhook delivery ID
        """
        self.processed_deliveries.add(delivery_id)
        self._delivery_order.append(delivery_id)

        # Cap at 10,000 entries
        if len(self.processed_deliveries) > 10000:
            oldest = self._delivery_order.popleft()
            self.processed_deliveries.discard(oldest)

    async def enqueue(self, job: Job) -> bool:
        """Enqueue a job.

        Args:
            job: Job to enqueue

        Returns:
            False if duplicate job_id, True if enqueued successfully
        """
        if job.job_id in self.jobs:
            self._logger.warning("duplicate_job", job_id=job.job_id)
            return False

        self.jobs[job.job_id] = job

        try:
            await asyncio.wait_for(self.queue.put(job), timeout=1.0)
            self._logger.info(
                "job_enqueued",
                job_id=job.job_id,
                issue_number=job.issue_number,
                queue_size=self.queue.qsize(),
            )
            return True
        except asyncio.TimeoutError:
            self._logger.error(
                "enqueue_timeout",
                job_id=job.job_id,
                issue_number=job.issue_number,
            )
            # Remove from jobs since we couldn't enqueue
            del self.jobs[job.job_id]
            return False

    async def worker(
        self, worker_id: int, process_fn: Callable[[Job], Awaitable[None]]
    ) -> None:
        """Worker loop that processes jobs.

        Args:
            worker_id: Worker identifier
            process_fn: Async function to process each job
        """
        logger = self._logger.bind(worker_id=worker_id)
        logger.info("worker_started")

        while True:
            try:
                job = await self.queue.get()
                logger = logger.bind(job_id=job.job_id, issue_number=job.issue_number)

                # Update state to RUNNING
                job.state = JobState.RUNNING
                logger.info("job_started", state=job.state.value)

                try:
                    await process_fn(job)
                    job.state = JobState.COMPLETED
                    logger.info("job_completed", state=job.state.value)
                except Exception as e:
                    job.state = JobState.FAILED
                    job.error = str(e)
                    logger.error(
                        "job_failed",
                        state=job.state.value,
                        error=str(e),
                        exc_info=True,
                    )
                finally:
                    self.queue.task_done()

            except asyncio.CancelledError:
                logger.info("worker_cancelled")
                break
            except Exception as e:
                logger.error("worker_error", error=str(e), exc_info=True)
                # Continue running to prevent worker death

    async def start_workers(
        self, num_workers: int, process_fn: Callable[[Job], Awaitable[None]]
    ) -> None:
        """Start worker tasks.

        Args:
            num_workers: Number of workers to start
            process_fn: Async function to process each job
        """
        self._logger.info("starting_workers", num_workers=num_workers)
        for i in range(num_workers):
            task = asyncio.create_task(self.worker(i, process_fn))
            self._worker_tasks.append(task)

    async def shutdown(self) -> None:
        """Gracefully shutdown workers."""
        self._logger.info("shutting_down_workers", num_workers=len(self._worker_tasks))
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()

    def get_job(self, job_id: str) -> Job | None:
        """Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job if found, None otherwise
        """
        return self.jobs.get(job_id)
