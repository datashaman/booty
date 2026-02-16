"""Planner input normalization — GitHub issue, CLI text, Observability incident."""

import re
from typing import Literal

from github import Auth, Github, GithubException
from pydantic import BaseModel, Field

from booty.planner.jobs import PlannerJob


class PlannerInput(BaseModel):
    """Normalized input for Planner Agent."""

    goal: str
    body: str
    labels: list[str] = Field(default_factory=list)
    source_type: Literal["incident", "feature_request", "bug", "unknown"] = "unknown"
    metadata: dict = Field(default_factory=dict)
    incident_fields: dict | None = None
    repo_context: dict | None = None


BODY_TRIM_CHARS = 8000
GOAL_TRIM_CHARS = 200

LABEL_TO_SOURCE: dict[str, str] = {
    "agent:incident": "incident",
    "bug": "bug",
    "enhancement": "feature_request",
}


def _looks_like_sentry_body(body: str) -> bool:
    """Return True if body contains BOTH '**Severity:**' AND '**Sentry:**'."""
    return "**Severity:**" in body and "**Sentry:**" in body


def _looks_like_sentry_title(title: str) -> bool:
    """Return True if title matches [severity] bracket-prefix pattern."""
    return bool(re.match(r"^\[(error|warning|info|debug)\]", title))


def derive_source_type(labels: list[str], body: str, title: str) -> str:
    """Derive source_type from labels or Sentry heuristics."""
    for lbl in labels:
        if lbl in LABEL_TO_SOURCE:
            return LABEL_TO_SOURCE[lbl]
    if _looks_like_sentry_body(body) or _looks_like_sentry_title(title):
        return "incident"
    return "unknown"


def _extract_incident_fields(body: str) -> dict:
    """Extract location and sentry_url from Sentry-style body markers."""
    result: dict[str, str] = {}
    for line in body.splitlines():
        if line.startswith("**Location:**"):
            result["location"] = line.replace("**Location:**", "").strip()
        elif line.startswith("**Sentry:**"):
            result["sentry_url"] = line.replace("**Sentry:**", "").strip()
    return result


def get_repo_context(
    owner: str, repo: str, token: str, max_depth: int = 2
) -> dict | None:
    """Fetch optional repo context: default branch and shallow file tree.

    Returns None on auth/404 errors.
    """
    try:
        g = Github(auth=Auth.Token(token))
        gh_repo = g.get_repo(f"{owner}/{repo}")
        default_branch = gh_repo.default_branch or "main"

        def _walk(path: str, depth: int) -> list[dict]:
            if depth > max_depth:
                return []
            contents = gh_repo.get_contents(path or "", ref=default_branch)
            result: list[dict] = []
            for c in contents:
                result.append({"path": c.path, "type": c.type})
                if c.type == "dir" and depth < max_depth:
                    result.extend(_walk(c.path, depth + 1))
            return result

        tree = _walk("", 0)
        return {"default_branch": default_branch, "tree": tree}
    except GithubException:
        return None


def normalize_github_issue(
    issue: dict,
    repo_info: dict | None = None,
    repo_context: dict | None = None,
) -> PlannerInput:
    """Normalize GitHub issue into PlannerInput."""
    title = issue.get("title") or "Untitled"
    body = (issue.get("body") or "")[:BODY_TRIM_CHARS]
    labels = [l.get("name", "") for l in issue.get("labels", [])]
    source_type = derive_source_type(labels, body, title)
    incident_fields = _extract_incident_fields(body) if source_type == "incident" else None

    metadata: dict = dict(repo_info) if repo_info else {}
    if url := issue.get("html_url"):
        metadata["issue_url"] = url
    if num := issue.get("number"):
        metadata["issue_number"] = num

    return PlannerInput(
        goal=title,
        body=body,
        labels=labels,
        source_type=source_type,
        metadata=metadata,
        incident_fields=incident_fields,
        repo_context=repo_context,
    )


def normalize_cli_text(
    text: str,
    repo_info: dict | None = None,
    repo_context: dict | None = None,
) -> PlannerInput:
    """Normalize CLI free text into PlannerInput. First line = goal, remainder = body."""
    if "\n" in text:
        goal, body = text.split("\n", 1)
    else:
        goal, body = text, ""
    goal = goal[:GOAL_TRIM_CHARS]
    body = body[:BODY_TRIM_CHARS]
    metadata = dict(repo_info) if repo_info else {}
    return PlannerInput(
        goal=goal,
        body=body,
        labels=[],
        source_type="unknown",
        metadata=metadata,
        incident_fields=None,
        repo_context=repo_context,
    )


def normalize_from_job(
    job: PlannerJob,
    repo_context: dict | None = None,
) -> PlannerInput:
    """Normalize PlannerJob payload into PlannerInput."""
    issue = job.payload.get("issue", {})
    repo_info = {"owner": job.owner, "repo": job.repo}
    return normalize_github_issue(issue, repo_info, repo_context)
