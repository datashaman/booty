"""GitHub issue creation from Sentry events."""

import json
import os
import time
from urllib.parse import urlparse

from github import Auth, Github, GithubException
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from booty.config import get_settings
from booty.logging import get_logger

logger = get_logger()


def build_sentry_issue_title(event: dict) -> str:
    """Build issue title from Sentry event.

    Pattern: [severity] ExceptionType — path/to/file.py:line
    Never include full message (volatile, breaks dedup).
    """
    level = event.get("level", "error")
    meta = event.get("metadata", {})
    ex_type = (
        meta.get("type")
        or event.get("exception", {}).get("values", [{}])[0].get("type")
        or "Error"
    )
    filename = (meta.get("filename") or "").strip() or "unknown"
    return f"[{level}] {ex_type} — {filename}"


def build_sentry_issue_body(event: dict, web_url: str) -> str:
    """Build issue body from Sentry event.

    Order: severity/env/release, first/last seen, Sentry link,
    location, top 7 frames, breadcrumb excerpt.
    """
    parts = []

    level = event.get("level", "error")
    tags = event.get("tags", [])
    env = event.get("environment", "")
    if not env and tags:
        for t in tags:
            if isinstance(t, list) and len(t) >= 2 and t[0] == "environment":
                env = t[1]
                break
    release = event.get("release", "")
    parts.append(f"**Severity:** {level}")
    if env:
        parts.append(f"**Environment:** {env}")
    if release:
        parts.append(f"**Release:** {release}")
    parts.append("")

    dt = event.get("datetime") or event.get("timestamp")
    if dt:
        parts.append(f"**First/Last seen:** {dt}")
    parts.append("")

    if web_url:
        parts.append(f"**Sentry:** {web_url}")
        parts.append("")

    culprit = event.get("culprit", "")
    meta = event.get("metadata", {})
    location = meta.get("filename") or culprit or "unknown"
    parts.append(f"**Location:** {location}")
    parts.append("")

    exc_values = event.get("exception", {}).get("values", [])
    if exc_values:
        frames = exc_values[0].get("stacktrace", {}).get("frames", [])
        if frames:
            parts.append("**Stack trace (top 7):**")
            for f in frames[-7:]:
                fn = f.get("filename", "?")
                line = f.get("line", "?")
                func = f.get("function", "")
                parts.append(f"- `{fn}:{line}` {func}")
            parts.append("")

    breadcrumbs = event.get("breadcrumbs", {}).get("values", [])[:8]
    if breadcrumbs:
        parts.append("**Breadcrumbs:**")
        for b in breadcrumbs:
            if b.get("level") == "debug":
                continue
            msg = (b.get("message") or str(b))[:160]
            parts.append(f"- {msg}")
        parts.append("")

    return "\n".join(parts)


def create_issue_from_sentry_event(
    event: dict,
    github_token: str,
    repo_url: str,
    label: str = "agent:builder",
) -> int | None:
    """Create GitHub issue from Sentry event.

    Returns:
        Issue number on success, None on failure.
    """
    parsed = urlparse(repo_url)
    path = parsed.path
    if path.startswith("/"):
        path = path[1:]
    if path.endswith(".git"):
        path = path[:-4]
    owner_repo = path

    g = Github(auth=Auth.Token(github_token))
    repo = g.get_repo(owner_repo)

    title = build_sentry_issue_title(event)
    web_url = event.get("web_url", "")
    body = build_sentry_issue_body(event, web_url)

    issue = repo.create_issue(title=title, body=body)
    try:
        issue.add_to_labels(label)
    except GithubException as e:
        if e.status == 404:
            repo.create_label(label, "0366d6", "Created by Booty Observability")
            issue.add_to_labels(label)
        else:
            raise
    return issue.number


def _spool_failed_sentry_event(event: dict, error: str) -> None:
    """Append failed event to disk spool for manual retry."""
    path = os.environ.get("OBSV_SPOOL_PATH", "/tmp/booty-sentry-spool.jsonl")
    line = json.dumps({"ts": time.time(), "event": event, "error": error}) + "\n"
    try:
        # Create parent directory if it doesn't exist (empty string means current directory)
        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(path, "a") as f:
            f.write(line)
        logger.warning(
            "observability_spooled",
            issue_id=event.get("issue_id"),
            error=error,
        )
    except (OSError, IOError) as e:
        logger.critical(
            "observability_spool_failed",
            issue_id=event.get("issue_id"),
            error=error,
            spool_error=str(e),
            path=path,
        )


def _retry_if_server_error(exception: BaseException) -> bool:
    """Retry on 5xx and network errors, not 4xx."""
    if isinstance(exception, GithubException):
        if exception.status and 400 <= exception.status < 500:
            return False
        return True
    return True


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception(_retry_if_server_error),
)
def _create_with_retry(
    event: dict,
    github_token: str,
    repo_url: str,
    label: str,
) -> int:
    """Create issue with tenacity retry. Raises after 3 failures."""
    return create_issue_from_sentry_event(
        event, github_token, repo_url, label
    )


def create_sentry_issue_with_retry(
    event: dict,
    github_token: str,
    repo_url: str,
    label: str = "agent:builder",
) -> int | None:
    """Create GitHub issue with retry. Spools to disk on persistent failure."""
    from tenacity import RetryError

    try:
        return _create_with_retry(event, github_token, repo_url, label)
    except RetryError as e:
        _spool_failed_sentry_event(event, str(e.last_attempt.exception()))
        return None
    except (GithubException, OSError) as e:
        _spool_failed_sentry_event(event, str(e))
        return None
