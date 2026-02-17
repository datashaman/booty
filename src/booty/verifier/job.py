"""Verifier job definition."""

from dataclasses import dataclass

import asyncio


@dataclass
class VerifierJob:
    """Verification job for a pull request."""

    job_id: str
    owner: str
    repo_name: str
    pr_number: int
    head_sha: str
    head_ref: str
    repo_url: str
    installation_id: int
    payload: dict
    is_agent_pr: bool = False
    issue_number: int | None = None
    cancel_event: asyncio.Event | None = None  # Queue sets for cancel signaling
