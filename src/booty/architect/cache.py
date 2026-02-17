"""Architect cache — plan_hash reuse, find_cached_architect_result, save_architect_result."""

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from booty.planner.cache import is_plan_fresh, plan_hash as _plan_hash
from booty.planner.schema import Plan
from booty.planner.store import get_planner_state_dir


def architect_plan_hash(plan: Plan) -> str:
    """Deterministic hash of plan content, excluding metadata. Reuses planner.cache.plan_hash."""
    return _plan_hash(plan)


def get_architect_cache_dir(state_dir: Path | None = None) -> Path:
    """Return architect cache base directory: state_dir/architect.

    Uses same base as Planner: state_dir or get_planner_state_dir().
    Dir is created in save, not here.
    """
    sd = state_dir or get_planner_state_dir()
    return sd / "architect"


def _architect_cache_path(
    owner: str,
    repo: str,
    issue_number: int,
    plan_hash_val: str,
    state_dir: Path | None = None,
) -> Path:
    """Return path for architect cache entry: state_dir/architect/owner/repo/issue_number/plan_hash.json."""
    base = get_architect_cache_dir(state_dir)
    return base / owner / repo / str(issue_number) / f"{plan_hash_val}.json"


@dataclass
class ArchitectCacheEntry:
    """Cached Architect result: approved or blocked."""

    created_at: str
    approved: bool
    plan: dict | None
    architect_notes: str | None
    block_reason: str | None


def find_cached_architect_result(
    owner: str,
    repo: str,
    issue_number: int,
    plan_hash_val: str,
    ttl_hours: float | None = None,
    state_dir: Path | None = None,
) -> ArchitectCacheEntry | None:
    """Return cached Architect result when plan_hash matches and within TTL, else None."""
    ttl = ttl_hours if ttl_hours is not None else float(
        os.environ.get("ARCHITECT_CACHE_TTL_HOURS", "24")
    )
    path = _architect_cache_path(owner, repo, issue_number, plan_hash_val, state_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    created_str = data.get("created_at")
    if not created_str:
        return None
    try:
        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        if not is_plan_fresh(created, ttl):
            return None
    except (ValueError, TypeError):
        return None
    return ArchitectCacheEntry(
        created_at=data["created_at"],
        approved=data.get("approved", False),
        plan=data.get("plan"),
        architect_notes=data.get("architect_notes"),
        block_reason=data.get("block_reason"),
    )


def save_architect_result(
    owner: str,
    repo: str,
    issue_number: int,
    plan_hash_val: str,
    approved: bool,
    plan: dict | None = None,
    architect_notes: str | None = None,
    block_reason: str | None = None,
    state_dir: Path | None = None,
) -> Path:
    """Save Architect result atomically. Creates parent dirs."""
    created_at = datetime.now(timezone.utc).isoformat()
    data = {
        "created_at": created_at,
        "approved": approved,
        "plan": plan,
        "architect_notes": architect_notes,
        "block_reason": block_reason,
    }
    path = _architect_cache_path(owner, repo, issue_number, plan_hash_val, state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    )
    try:
        json.dump(data, fd, indent=0, separators=(",", ":"), default=str)
        fd.flush()
        os.fsync(fd.fileno())
        fd.close()
        os.replace(fd.name, path)
    except Exception:
        if os.path.exists(fd.name):
            os.unlink(fd.name)
        raise
    return path
