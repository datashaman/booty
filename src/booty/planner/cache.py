"""Planner cache — input_hash, plan_hash, TTL, lookup."""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from booty.planner.input import PlannerInput
from booty.planner.schema import Plan
from booty.planner.store import get_planner_state_dir, load_plan, plan_path_for_issue


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
    created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
    if not is_plan_fresh(created, ttl):
        return None
    return plan
