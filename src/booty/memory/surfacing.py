"""Memory surfacing — surface related history into PR comments and incident issues."""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from github import Github

from booty.github.comments import post_memory_comment
from booty.logging import get_logger
from booty.memory import lookup

logger = get_logger()

if TYPE_CHECKING:
    from booty.memory.config import MemoryConfig

MARKER = "<!-- booty-memory -->"
GOV_SECTION_HEADER = "### Related to this hold"


def _find_pr_for_commit(gh_repo, head_sha: str) -> int | None:
    """Find PR number for a commit. Returns first PR number if any, else None."""
    try:
        commit = gh_repo.get_commit(head_sha)
        pulls = commit.get_pulls()
        for pr in pulls:
            return pr.number
        return None
    except Exception:
        return None


def build_related_history_for_incident(
    event: dict,
    repo: str,
    mem_config: "MemoryConfig",
    state_dir: Path | None = None,
) -> str:
    """Build 'Related history' section for Observability incident issue body.

    Returns empty string if comment_on_incident_issue disabled or zero matches.
    Derives paths from stack frames, culprit, metadata.
    """
    if not mem_config.comment_on_incident_issue:
        return ""

    paths: list[str] = []
    exc_values = event.get("exception", {}).get("values", [])
    if exc_values:
        frames = exc_values[0].get("stacktrace", {}).get("frames", [])
        for f in frames[-7:]:
            fn = f.get("filename")
            if fn:
                paths.append(fn)
    culprit = event.get("culprit", "")
    if culprit:
        paths.append(culprit)
    meta = event.get("metadata", {})
    meta_fn = meta.get("filename")
    if meta_fn:
        paths.append(meta_fn)
    paths = [p for p in paths if p and p.strip()]

    fingerprint = None
    tags = event.get("tags", [])
    for t in tags:
        if isinstance(t, (list, tuple)) and len(t) >= 2 and t[0] == "fingerprint":
            fingerprint = str(t[1]) if t[1] else None
            break

    matches = lookup.query(
        paths=paths,
        repo=repo,
        fingerprint=fingerprint,
        config=mem_config,
        state_dir=state_dir,
    )
    if not matches:
        return ""

    lines = []
    for m in matches:
        rec_type = m.get("type", "unknown")
        ts = m.get("timestamp", "")
        summary = m.get("summary", "")
        links = m.get("links") or []
        link = links[0] if links else ""
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            date_str = ts[:10] if ts else ""
        line = f"- **{rec_type}** ({date_str}) — {summary}"
        if link:
            line += f" — {link}"
        lines.append(line)

    return "**Related history:**\n\n" + "\n".join(lines)


def format_matches_for_pr(matches: list[dict]) -> str:
    """Format memory matches for PR comment display.

    Each match has type, timestamp, summary, links, id (from lookup.result_subset).
    Format per match: "- **{type}** ({date}) — {summary} {link}"
    Deduplicates by (type, summary, date) to avoid duplicate entries (e.g. same security_block twice).
    """
    if not matches:
        return ""

    seen: set[tuple[str, str, str]] = set()
    lines = []
    for m in matches:
        rec_type = m.get("type", "unknown")
        ts = m.get("timestamp", "")
        summary = m.get("summary", "")
        links = m.get("links") or []
        link = links[0] if links else ""
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            date_str = ts[:10] if ts else ""
        key = (rec_type, summary, date_str)
        if key in seen:
            continue
        seen.add(key)
        line = f"- **{rec_type}** ({date_str}) — {summary}"
        if link:
            line += f" {link}"
        lines.append(line)
    return "\n".join(lines)


def surface_pr_comment(
    github_token: str,
    repo_url: str,
    pr_number: int,
    paths: list[str],
    repo: str,
    mem_config: "MemoryConfig",
    state_dir: Path | None = None,
) -> None:
    """Surface memory as PR comment after Verifier check completion.

    If comment_on_pr disabled or zero matches, omits comment entirely.
    """
    if not mem_config.comment_on_pr:
        return

    matches = lookup.query(
        paths=paths,
        repo=repo,
        config=mem_config,
        state_dir=state_dir,
    )
    if not matches:
        return

    body = format_matches_for_pr(matches)
    post_memory_comment(github_token, repo_url, pr_number, body)


def surface_governor_hold(
    github_token: str,
    repo_full_name: str,
    head_sha: str,
    hold_reason: str,
    mem_config: "MemoryConfig",
    state_dir: Path | None = None,
) -> None:
    """Surface Governor HOLD memory matches in PR comment.

    Finds PR for commit, runs fingerprint lookup, merges '### Related to this hold'
    section into existing Memory comment or creates new.
    Skips when comment_on_pr disabled, no PR found, or zero matches.
    """
    if not mem_config.comment_on_pr:
        return

    try:
        gh = Github(github_token)
        repo = gh.get_repo(repo_full_name)
        pr_number = _find_pr_for_commit(repo, head_sha)
        if not pr_number:
            return

        matches = lookup.query(
            paths=[],
            repo=repo_full_name,
            fingerprint=hold_reason,
            config=mem_config,
            state_dir=state_dir,
            max_matches=2,
        )
        if not matches:
            return

        formatted = format_matches_for_pr(matches)
        repo_url = f"https://github.com/{repo_full_name}"
        issue = repo.get_issue(pr_number)

        for comment in issue.get_comments():
            if MARKER not in (comment.body or ""):
                continue
            current_body = comment.body or ""
            if GOV_SECTION_HEADER in current_body:
                idx = current_body.find(GOV_SECTION_HEADER)
                marker_idx = current_body.find(MARKER)
                if marker_idx >= 0:
                    before = current_body[:idx].rstrip()
                    after = current_body[marker_idx:]
                    new_body = f"{before}\n\n{GOV_SECTION_HEADER}\n\n{formatted}\n\n{after}"
                else:
                    new_body = current_body
            else:
                new_body = current_body.replace(
                    MARKER,
                    f"\n\n{GOV_SECTION_HEADER}\n\n{formatted}\n\n{MARKER}",
                    1,
                )
            comment.edit(new_body)
            return

        body = f"## Memory: related history\n\n{GOV_SECTION_HEADER}\n\n{formatted}\n\n{MARKER}"
        post_memory_comment(github_token, repo_url, pr_number, body)
    except Exception as e:
        logger.warning(
            "governor_hold_surfacing_failed",
            repo=repo_full_name,
            head_sha=head_sha[:7] if head_sha else "?",
            error=str(e),
        )
