"""Architect job queue and idempotency.

WIRE-02: Webhook-triggered Architect (e.g. user adds label to issue with existing plan)
uses ArchitectJob, architect_queue, and architect worker. Dedup by (repo, plan_hash).
"""

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Deque, Set


@dataclass
class ArchitectJob:
    """Architect job — issue with plan to review."""

    job_id: str
    issue_number: int
    issue_url: str
    repo_url: str
    owner: str
    repo: str
    payload: dict
    plan_hash: str


architect_queue: asyncio.Queue[ArchitectJob] = asyncio.Queue()
architect_processed: Set[str] = set()
_architect_processed_order: Deque[str] = deque()
ARCHITECT_PROCESSED_CAP = 1000


def architect_is_duplicate(repo_full_name: str, plan_hash: str) -> bool:
    """Check if (repo, plan_hash) was already processed."""
    key = f"{repo_full_name}:{plan_hash}"
    return key in architect_processed


def architect_mark_processed(repo_full_name: str, plan_hash: str) -> None:
    """Mark (repo, plan_hash) as processed. Cap size; evict oldest."""
    key = f"{repo_full_name}:{plan_hash}"
    architect_processed.add(key)
    _architect_processed_order.append(key)
    while len(architect_processed) > ARCHITECT_PROCESSED_CAP:
        oldest = _architect_processed_order.popleft()
        architect_processed.discard(oldest)


async def architect_enqueue(job: ArchitectJob) -> bool:
    """Enqueue architect job. Returns True if enqueued, False on TimeoutError."""
    try:
        await asyncio.wait_for(architect_queue.put(job), timeout=1.0)
        return True
    except asyncio.TimeoutError:
        return False
