"""Architect metrics — plans_reviewed, plans_rewritten, architect_blocks, cache_hits (ARCH-33)."""

import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from booty.planner.store import get_planner_state_dir


def get_architect_metrics_dir(state_dir: Path | None = None) -> Path:
    """Return architect metrics directory: state_dir/architect or get_planner_state_dir()/architect."""
    sd = state_dir or get_planner_state_dir()
    return sd / "architect"


def _metrics_path(state_dir: Path | None = None) -> Path:
    """Path to metrics.json (events array)."""
    return get_architect_metrics_dir(state_dir) / "metrics.json"


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


def _append_event(event_type: str, state_dir: Path | None = None) -> None:
    """Append event with current UTC timestamp."""
    ts = datetime.now(timezone.utc).isoformat()
    events = _load_events(state_dir)
    events.append({"ts": ts, "type": event_type})
    _save_events(events, state_dir)


def increment_reviewed(state_dir: Path | None = None) -> None:
    """Increment plans_reviewed (approved without rewrite)."""
    _append_event("approved", state_dir)


def increment_rewritten(state_dir: Path | None = None) -> None:
    """Increment plans_rewritten (approved after rewrite)."""
    _append_event("rewritten", state_dir)


def increment_blocked(state_dir: Path | None = None) -> None:
    """Increment architect_blocks (plan blocked)."""
    _append_event("blocked", state_dir)


def increment_cache_hit(state_dir: Path | None = None) -> None:
    """Increment cache_hits (reused cached Architect result)."""
    _append_event("cache_hit", state_dir)


def get_24h_stats(state_dir: Path | None = None) -> dict[str, int]:
    """Return counts for events within last 24h. Rolling window from now."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    events = _load_events(state_dir)
    approved = rewritten = blocked = cache_hits = 0
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
        if t == "approved":
            approved += 1
        elif t == "rewritten":
            rewritten += 1
        elif t == "blocked":
            blocked += 1
        elif t == "cache_hit":
            cache_hits += 1
    return {
        "approved": approved,
        "rewritten": rewritten,
        "blocked": blocked,
        "cache_hits": cache_hits,
    }
