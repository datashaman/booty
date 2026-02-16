"""Planner cache — input_hash, plan_hash, TTL, lookup."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from booty.planner.input import PlannerInput
from booty.planner.schema import Plan
from booty.planner.store import (
    get_planner_state_dir,
    load_plan,
    plan_path_for_ad_hoc_from_input,
    plan_path_for_issue,
    save_plan,
)


def _canonical_input(inp: PlannerInput) -> dict:
    """Build dict for hashing; exclude metadata."""
    d: dict = {
        "goal": inp.goal.strip(),
        "body": inp.body.strip(),
        "labels": sorted(inp.labels),
        "source_type": inp.source_type,
    }
    if inp.incident_fields:
        d["incident_fields"] = dict(sorted(inp.incident_fields.items()))
    if inp.repo_context and "default_branch" in inp.repo_context:
        d["default_branch"] = inp.repo_context["default_branch"]
    return d


def input_hash(inp: PlannerInput) -> str:
    """Deterministic hash from canonical PlannerInput. Same canonical input yields same hash."""
    canon = json.dumps(_canonical_input(inp), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def _plan_content_for_hash(plan: Plan) -> dict:
    """Fields included in plan_hash — excludes metadata (created_at, input_hash, plan_hash)."""
    d = plan.model_dump()
    d.pop("metadata", None)
    return d


def plan_hash(plan: Plan) -> str:
    """Deterministic hash of plan content, excluding metadata."""
    canon = json.dumps(
        _plan_content_for_hash(plan), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canon.encode()).hexdigest()


def is_plan_fresh(created_at: datetime, ttl_hours: float = 24) -> bool:
    """True if plan is within TTL. created_at must be UTC-aware."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=ttl_hours)
    return created_at >= cutoff


def find_cached_issue_plan(
    owner: str,
    repo: str,
    issue_number: int,
    input_hash_val: str,
    ttl_hours: float | None = None,
    state_dir: Path | None = None,
) -> Plan | None:
    """Return cached plan when input_hash matches and within TTL, else None."""
    ttl = ttl_hours if ttl_hours is not None else float(
        os.environ.get("PLANNER_CACHE_TTL_HOURS", "24")
    )
    path = plan_path_for_issue(owner, repo, issue_number, state_dir)
    plan = load_plan(path)
    if not plan:
        return None
    stored_hash = plan.metadata.get("input_hash")
    if stored_hash != input_hash_val:
        return None
    created_str = plan.metadata.get("created_at")
    if not created_str:
        return None
    try:
        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        if not is_plan_fresh(created, ttl):
            return None
    except (ValueError, TypeError):
        return None
    return plan


def _ad_hoc_index_path(state_dir: Path | None = None) -> Path:
    """Path to ad-hoc index: state_dir/plans/ad-hoc/index.json."""
    sd = state_dir or get_planner_state_dir()
    return sd / "plans" / "ad-hoc" / "index.json"


def find_cached_ad_hoc_plan(
    input_hash_val: str,
    ttl_hours: float | None = None,
    state_dir: Path | None = None,
) -> Plan | None:
    """Return cached ad-hoc plan when input_hash matches and within TTL, else None."""
    ttl = ttl_hours if ttl_hours is not None else float(
        os.environ.get("PLANNER_CACHE_TTL_HOURS", "24")
    )
    index_path = _ad_hoc_index_path(state_dir)
    if not index_path.exists():
        return None
    try:
        data = json.loads(index_path.read_text())
        filename = data.get(input_hash_val)
        if not filename:
            return None
        plan_path = index_path.parent / filename
        plan = load_plan(plan_path)
        if not plan:
            return None
        created_str = plan.metadata.get("created_at")
        if not created_str:
            return None
        try:
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            if not is_plan_fresh(created, ttl):
                return None
        except (ValueError, TypeError):
            return None
        return plan
    except (json.JSONDecodeError, OSError):
        return None


def save_ad_hoc_plan(
    plan: Plan,
    inp: PlannerInput,
    state_dir: Path | None = None,
) -> Path:
    """Save ad-hoc plan to timestamped path and update hash index. Returns path."""
    h = input_hash(inp)
    path = plan_path_for_ad_hoc_from_input(h, state_dir)
    if not plan.metadata.get("created_at"):
        merged = plan.metadata | {
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        plan = plan.model_copy(update={"metadata": merged})
    path.parent.mkdir(parents=True, exist_ok=True)
    save_plan(plan, path)
    index_path = _ad_hoc_index_path(state_dir)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_data: dict = {}
    if index_path.exists():
        try:
            index_data = json.loads(index_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    index_data[h] = path.name
    fd = tempfile.NamedTemporaryFile(
        mode="w",
        dir=index_path.parent,
        delete=False,
        suffix=".tmp",
    )
    try:
        json.dump(index_data, fd, indent=0, separators=(",", ":"))
        fd.flush()
        os.fsync(fd.fileno())
        fd.close()
        os.replace(fd.name, index_path)
    except Exception:
        if os.path.exists(fd.name):
            os.unlink(fd.name)
        raise
    return path
