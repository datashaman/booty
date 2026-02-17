"""Promotion gate helpers — plan-originated detection and Architect approval (PROMO-02)."""

import re
from pathlib import Path
from urllib.parse import urlparse

from booty.github.comments import get_plan_comment_body
from booty.architect.artifact import load_architect_plan_for_issue


def _parse_owner_repo(repo_url: str) -> tuple[str, str] | None:
    """Parse owner and repo from repo_url. Returns (owner, repo) or None."""
    parsed = urlparse(repo_url)
    path = parsed.path
    if path.startswith("/"):
        path = path[1:]
    if path.endswith(".git"):
        path = path[:-4]
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return None


def is_plan_originated_pr(
    github_token: str, repo_url: str, issue_number: int | None
) -> bool:
    """True if PR is plan-originated: issue has a plan comment or Architect artifact.

    If issue_number is None, returns False (indeterminate — skip Architect gate).

    Checks: (1) get_plan_comment_body for <!-- booty-plan -->; (2) fallback to
    load_architect_plan_for_issue if plan comment unavailable.
    """
    if issue_number is None:
        return False
    body = get_plan_comment_body(github_token, repo_url, issue_number)
    if body is not None and "<!-- booty-plan -->" in body:
        return True
    parsed = _parse_owner_repo(repo_url)
    if parsed is not None:
        owner, repo = parsed
        artifact = load_architect_plan_for_issue(owner, repo, issue_number)
        if artifact is not None:
            return True
    return False


def architect_approved_for_issue(
    github_token: str,
    repo_url: str,
    issue_number: int,
    owner: str,
    repo: str,
    state_dir: Path | None = None,
) -> bool:
    """True if Architect has approved for this issue.

    Sources: (1) Plan comment <!-- booty-architect --> block with ✓ Approved;
    (2) Disk artifact as advisory fallback. GitHub wins; disk is advisory.
    """
    body = get_plan_comment_body(github_token, repo_url, issue_number)
    if body is not None:
        match = re.search(
            r"<!-- booty-architect -->.*?<!-- /booty-architect -->",
            body,
            re.DOTALL,
        )
        if match and "✓ Approved" in (match.group(0) or ""):
            return True
    artifact = load_architect_plan_for_issue(owner, repo, issue_number, state_dir)
    if artifact is not None:
        return True
    return False
