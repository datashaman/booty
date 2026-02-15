"""Verification workspace preparation."""

import asyncio
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

import git

from booty.logging import get_logger

logger = get_logger()


@dataclass
class Workspace:
    """Verification workspace with cloned repo at specific commit."""

    path: str
    repo: git.Repo
    branch: str


@asynccontextmanager
async def prepare_verification_workspace(
    repo_url: str, head_sha: str, github_token: str = "", head_ref: str = ""
) -> AsyncIterator[Workspace]:
    """Clone repo at head_sha in clean temp dir for verification.

    Creates a temporary directory, clones the repository (shallow),
    fetches and checks out the given head_sha. Cleans up on exit.

    Args:
        repo_url: Repository URL to clone
        head_sha: Commit SHA to checkout (PR head)
        github_token: Optional GitHub token for private repos

    Yields:
        Workspace containing path, repo, and branch (head_sha)
    """
    temp_dir = None
    repo = None

    try:
        temp_dir = tempfile.TemporaryDirectory(
            prefix="booty-verifier-", ignore_cleanup_errors=True
        )
        logger.info("verifier_workspace_created", path=temp_dir.name)

        clone_url = repo_url
        if github_token and repo_url.startswith("https://"):
            clone_url = repo_url.replace("https://", f"https://{github_token}@")

        def _clone():
            kwargs = {"depth": 50}
            if head_ref:
                kwargs["branch"] = head_ref
            return git.Repo.clone_from(clone_url, temp_dir.name, **kwargs)

        repo = await asyncio.get_running_loop().run_in_executor(None, _clone)
        logger.info("verifier_clone_complete", path=temp_dir.name, head_ref=head_ref or "default")

        def _fetch_checkout():
            if head_ref:
                repo.git.fetch("origin", head_ref)
            else:
                repo.git.fetch("origin")
            repo.git.checkout(head_sha)

        await asyncio.get_running_loop().run_in_executor(None, _fetch_checkout)
        logger.info("verifier_checkout_complete", head_sha=head_sha[:7])

        workspace = Workspace(path=temp_dir.name, repo=repo, branch=head_sha)
        yield workspace

    finally:
        if repo:
            repo.close()
        if temp_dir:
            temp_dir.cleanup()
            logger.info("verifier_workspace_cleaned")
