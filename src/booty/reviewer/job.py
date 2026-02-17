"""Reviewer job definition."""

from dataclasses import dataclass

import asyncio


@dataclass
class ReviewerJob:
    """Review job for an agent pull request."""

    job_id: str
    owner: str
    repo_name: str
    pr_number: int
    head_sha: str
    head_ref: str
    repo_url: str
    installation_id: int
    payload: dict
    is_agent_pr: bool = True  # Webhook only enqueues for agent PRs
    cancel_event: asyncio.Event | None = None  # Queue sets for cancel signaling
