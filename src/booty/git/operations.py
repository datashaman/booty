"""Git commit and push operations."""

import asyncio

import git

from booty.logging import get_logger

logger = get_logger()


def commit_changes(
    repo: git.Repo,
    file_paths: list[str],
    message: str,
    deleted_paths: list[str] | None = None,
) -> str:
    """Commit changes to repository.

    Args:
        repo: Git repository
        file_paths: List of file paths to add
        message: Commit message
        deleted_paths: Optional list of file paths to remove

    Returns:
        Commit SHA
    """
    # Stage files to add
    if file_paths:
        repo.index.add(file_paths)
        logger.info("files_staged", count=len(file_paths))

    # Stage files to remove
    if deleted_paths:
        repo.index.remove(deleted_paths)
        logger.info("files_removed", count=len(deleted_paths))

    # Commit changes
    commit = repo.index.commit(message)
    commit_sha = str(commit)

    logger.info("changes_committed", sha=commit_sha)
    return commit_sha


async def push_to_remote(repo: git.Repo, github_token: str = "") -> None:
    """Push branch to remote with optional token authentication.

    Args:
        repo: Git repository
        github_token: Optional GitHub token for authentication
    """
    # Get origin remote
    origin = repo.remote(name="origin")

    # If token provided, update remote URL to inject token
    if github_token:
        # Get current URL
        remote_url = next(origin.urls)

        # Inject token if https URL
        if remote_url.startswith("https://"):
            auth_url = remote_url.replace("https://", f"https://{github_token}@")
            origin.set_url(auth_url)
            logger.info("remote_url_updated", masked_token="***")

    # Push with upstream tracking (blocking I/O, run in executor)
    branch_name = repo.active_branch.name

    def _push():
        repo.git.push("--set-upstream", "origin", branch_name)

    await asyncio.get_running_loop().run_in_executor(None, _push)
    logger.info("push_complete", branch=branch_name)


def format_commit_message(
    commit_type: str, scope: str | None, summary: str, body: str, issue_number: int
) -> str:
    """Format conventional commit message with issue reference.

    Args:
        commit_type: Commit type (feat, fix, etc.)
        scope: Optional scope
        summary: Commit summary line
        body: Commit body
        issue_number: GitHub issue number

    Returns:
        Formatted commit message
    """
    # Format header with optional scope
    if scope:
        header = f"{commit_type}({scope}): {summary}"
    else:
        header = f"{commit_type}: {summary}"

    # Build full message with body and footers
    message = f"{header}\n\n{body}\n\nResolves #{issue_number}\n\nCo-Authored-By: Booty Agent <noreply@booty.dev>"

    return message
