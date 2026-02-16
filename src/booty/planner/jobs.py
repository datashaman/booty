"""Planner job queue and idempotency."""

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Deque, Set


@dataclass
class PlannerJob:
    """Planner job — issue to plan."""

    job_id: str
    issue_number: int
    issue_url: str
    repo_url: str
    owner: str
    repo: str
    payload: dict


planner_queue: asyncio.Queue[PlannerJob] = asyncio.Queue()
planner_processed_deliveries: Set[str] = set()
_planner_delivery_order: Deque[str] = deque()
PLANNER_PROCESSED_CAP = 10000


def planner_is_duplicate(delivery_id: str) -> bool:
    """Check if delivery ID was already processed."""
    return delivery_id in planner_processed_deliveries


def planner_mark_processed(delivery_id: str) -> None:
    """Mark delivery ID as processed."""
    planner_processed_deliveries.add(delivery_id)
    _planner_delivery_order.append(delivery_id)
    while len(planner_processed_deliveries) > PLANNER_PROCESSED_CAP:
        oldest = _planner_delivery_order.popleft()
        planner_processed_deliveries.discard(oldest)


async def planner_enqueue(job: PlannerJob) -> bool:
    """Enqueue planner job. Returns True if enqueued."""
    try:
        await asyncio.wait_for(planner_queue.put(job), timeout=1.0)
        return True
    except asyncio.TimeoutError:
        return False
