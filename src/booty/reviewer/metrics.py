"""Reviewer metrics — reviews_total, reviews_blocked, reviews_suggestions, reviewer_fail_open (REV-09, REV-15).

Uses same base state dir as Planner/Architect (get_planner_state_dir) for consistent
~/.booty/state layout; PLANNER_STATE_DIR env applies. Stored under state_dir/reviewer/.
"""

import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from booty.planner.store import get_planner_state_dir

FAIL_OPEN_BUCKETS = frozenset({
    "diff_fetch_failed",
    "github_api_failed",
    "llm_timeout",
    "llm_error",
    "schema_parse_failed",
    "unexpected_exception",
})


def get_reviewer_metrics_dir(state_dir: Path | None = None) -> Path:
    """Return reviewer metrics directory: state_dir/reviewer or shared base state/reviewer."""
    sd = state_dir or get_planner_state_dir()
    return sd / "reviewer"


def _metrics_path(state_dir: Path | None = None) -> Path:
    """Path to metrics.json (events array)."""
    return get_reviewer_metrics_dir(state_dir) / "metrics.json"


def _load_events(state_dir: Path | None = None) -> list[dict]:
    """Load events from metrics.json. Returns empty list if missing or invalid."""
    path = _metrics_path(state_dir)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data.get("events") or []
    except (json.JSONDecodeError, TypeError):
        return []


def _save_events(events: list[dict], state_dir: Path | None = None) -> None:
    """Persist events to metrics.json atomically."""
    path = _metrics_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"events": events}
    fd = tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    )
    try:
        json.dump(data, fd, indent=0, separators=(",", ":"))
        fd.flush()
        os.fsync(fd.fileno())
        fd.close()
        os.replace(fd.name, path)
    except Exception:
        if os.path.exists(fd.name):
            os.unlink(fd.name)
        raise


def _append_event(
    event_type: str,
    state_dir: Path | None = None,
    *,
    bucket: str | None = None,
) -> None:
    """Append event with current UTC timestamp."""
    ts = datetime.now(timezone.utc).isoformat()
    events = _load_events(state_dir)
    event: dict = {"ts": ts, "type": event_type}
    if bucket is not None:
        event["bucket"] = bucket
    events.append(event)
    _save_events(events, state_dir)


def increment_reviews_total(state_dir: Path | None = None) -> None:
    """Increment reviews_total (every completed review)."""
    _append_event("total", state_dir)


def increment_reviews_blocked(state_dir: Path | None = None) -> None:
    """Increment reviews_blocked (review blocked)."""
    _append_event("blocked", state_dir)


def increment_reviews_suggestions(state_dir: Path | None = None) -> None:
    """Increment reviews_suggestions (approved with suggestions)."""
    _append_event("suggestions", state_dir)


def increment_reviewer_fail_open(
    fail_open_type: str,
    state_dir: Path | None = None,
) -> None:
    """Increment reviewer_fail_open (fail-open triggered).

    Args:
        fail_open_type: Bucket: diff_fetch_failed, github_api_failed,
            llm_timeout, llm_error, schema_parse_failed, unexpected_exception
    """
    bucket = fail_open_type if fail_open_type in FAIL_OPEN_BUCKETS else "unexpected_exception"
    _append_event("fail_open", state_dir, bucket=bucket)


def get_reviewer_24h_stats(state_dir: Path | None = None) -> dict[str, int]:
    """Return counts for events within last 24h. Rolling window from now."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    events = _load_events(state_dir)
    reviews_total = reviews_blocked = reviews_suggestions = reviewer_fail_open = 0
    for e in events:
        ts_str = e.get("ts")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < cutoff:
                continue
        except (ValueError, TypeError):
            continue
        t = e.get("type", "")
        if t == "total":
            reviews_total += 1
        elif t == "blocked":
            reviews_blocked += 1
        elif t == "suggestions":
            reviews_suggestions += 1
        elif t == "fail_open":
            reviewer_fail_open += 1
    return {
        "reviews_total": reviews_total,
        "reviews_blocked": reviews_blocked,
        "reviews_suggestions": reviews_suggestions,
        "reviewer_fail_open": reviewer_fail_open,
    }
