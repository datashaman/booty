"""Memory surfacing — surface related history into PR comments and incident issues."""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from booty.github.comments import post_memory_comment
from booty.memory import lookup

if TYPE_CHECKING:
    from booty.memory.config import MemoryConfig


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
    """
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
