"""Repository management with workspace isolation."""

import asyncio
import os
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass

import git

from booty.jobs import Job
from booty.logging import get_logger


@dataclass
class Workspace:
    """Workspace data structure."""

    path: str
    repo: git.Repo
    branch: str


@asynccontextmanager
async def prepare_workspace(
    job: Job, repo_url: str, branch: str, github_token: str = ""
):
    """Prepare an isolated workspace for a job.

    Creates a temporary directory, clones the repository, and checks out
    a feature branch. Cleans up on exit.

    Args:
        job: Job being processed
        repo_url: Repository URL to clone
        branch: Base branch to clone
        github_token: Optional GitHub token for private repos

    Yields:
        Workspace containing path, repo, and branch
    """
    logger = get_logger().bind(job_id=job.job_id, issue_number=job.issue_number)
    temp_dir = None
    repo = None

    try:
        # Create temporary directory
        temp_dir = tempfile.TemporaryDirectory(
            prefix=f"booty-{job.issue_number}-", ignore_cleanup_errors=True
        )
        logger.info("workspace_created", path=temp_dir.name)

        # Construct clone URL with token if provided
        clone_url = repo_url
        if github_token and repo_url.startswith("https://"):
            # Inject token: https://token@github.com/...
            clone_url = repo_url.replace("https://", f"https://{github_token}@")

        # Clone repository (blocking I/O, run in executor)
        loop = asyncio.get_event_loop()

        def _clone():
            return git.Repo.clone_from(clone_url, temp_dir.name, branch=branch)

        repo = await loop.run_in_executor(None, _clone)
        logger.info("clone_complete", branch=branch, path=temp_dir.name)

        # Create and checkout feature branch
        feature_branch = f"agent/issue-{job.issue_number}"
        repo.git.checkout("-b", feature_branch)
        logger.info("branch_created", branch=feature_branch)

        # Yield workspace
        workspace = Workspace(path=temp_dir.name, repo=repo, branch=feature_branch)
        yield workspace

    finally:
        # Cleanup
        if repo:
            repo.close()
        if temp_dir:
            temp_dir.cleanup()
            logger.info("workspace_cleaned", job_id=job.job_id)
