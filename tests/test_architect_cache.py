"""Tests for Architect cache primitives."""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from booty.architect.cache import (
    architect_plan_hash,
    find_cached_architect_result,
    save_architect_result,
)
from booty.planner.schema import HandoffToBuilder, Plan, Step


def test_architect_plan_hash_excludes_metadata() -> None:
    """Two Plan instances with same content but different metadata yield same hash."""
    handoff = HandoffToBuilder(
        branch_name_hint="b", commit_message_hint="c", pr_title="t", pr_body_outline="o"
    )
    p1 = Plan(
        goal="g",
        steps=[Step(id="P1", action="read", path="x", acceptance="d")],
        handoff_to_builder=handoff,
        metadata={"created_at": "2026-01-01T00:00:00Z", "input_hash": "abc"},
    )
    p2 = Plan(
        goal="g",
        steps=[Step(id="P1", action="read", path="x", acceptance="d")],
        handoff_to_builder=handoff,
        metadata={"created_at": "2026-02-01T00:00:00Z", "input_hash": "xyz"},
    )
    assert architect_plan_hash(p1) == architect_plan_hash(p2)
    assert len(architect_plan_hash(p1)) == 64


def test_find_cached_architect_result_hit() -> None:
    """Save approved result; find with same plan_hash and TTL returns entry."""
    plan_dict = {
        "plan_version": "1",
        "goal": "g",
        "steps": [{"id": "P1", "action": "read", "path": "x", "acceptance": "d"}],
        "handoff_to_builder": {
            "branch_name_hint": "b",
            "commit_message_hint": "c",
            "pr_title": "t",
            "pr_body_outline": "o",
        },
    }
    plan_hash_val = architect_plan_hash(Plan.model_validate(plan_dict))
    with tempfile.TemporaryDirectory() as d:
        state_dir = Path(d)
        save_architect_result(
            "owner",
            "repo",
            1,
            plan_hash_val,
            approved=True,
            plan=plan_dict,
            architect_notes="notes",
            state_dir=state_dir,
        )
        cached = find_cached_architect_result(
            "owner", "repo", 1, plan_hash_val, ttl_hours=24.0, state_dir=state_dir
        )
        assert cached is not None
        assert cached.approved is True
        assert cached.plan == plan_dict
        assert cached.architect_notes == "notes"


def test_find_cached_architect_result_miss_hash() -> None:
    """Save for plan_hash A; find with plan_hash B returns None."""
    plan_dict = {
        "plan_version": "1",
        "goal": "g",
        "steps": [{"id": "P1", "action": "read", "path": "x", "acceptance": "d"}],
        "handoff_to_builder": {
            "branch_name_hint": "b",
            "commit_message_hint": "c",
            "pr_title": "t",
            "pr_body_outline": "o",
        },
    }
    plan_hash_val = architect_plan_hash(Plan.model_validate(plan_dict))
    with tempfile.TemporaryDirectory() as d:
        state_dir = Path(d)
        save_architect_result(
            "owner", "repo", 1, plan_hash_val, approved=True, plan=plan_dict, state_dir=state_dir
        )
        assert (
            find_cached_architect_result(
                "owner", "repo", 1, "wrong_hash_abc123", ttl_hours=24.0, state_dir=state_dir
            )
            is None
        )


def test_find_cached_architect_result_miss_expired() -> None:
    """Save with created_at in past; find with TTL returns None."""
    plan_dict = {
        "plan_version": "1",
        "goal": "g",
        "steps": [{"id": "P1", "action": "read", "path": "x", "acceptance": "d"}],
        "handoff_to_builder": {
            "branch_name_hint": "b",
            "commit_message_hint": "c",
            "pr_title": "t",
            "pr_body_outline": "o",
        },
    }
    plan_hash_val = architect_plan_hash(Plan.model_validate(plan_dict))
    with tempfile.TemporaryDirectory() as d:
        state_dir = Path(d)
        path = state_dir / "owner" / "repo" / "1" / f"{plan_hash_val}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        data = {
            "created_at": old_ts,
            "approved": True,
            "plan": plan_dict,
            "architect_notes": None,
            "block_reason": None,
        }
        path.write_text(json.dumps(data))
        assert (
            find_cached_architect_result(
                "owner", "repo", 1, plan_hash_val, ttl_hours=24.0, state_dir=state_dir
            )
            is None
        )


def test_save_architect_result_blocked() -> None:
    """Save blocked result; find returns approved=False, block_reason present."""
    plan_dict = {
        "plan_version": "1",
        "goal": "g",
        "steps": [{"id": "P1", "action": "read", "path": "x", "acceptance": "d"}],
        "handoff_to_builder": {
            "branch_name_hint": "b",
            "commit_message_hint": "c",
            "pr_title": "t",
            "pr_body_outline": "o",
        },
    }
    plan_hash_val = architect_plan_hash(Plan.model_validate(plan_dict))
    with tempfile.TemporaryDirectory() as d:
        state_dir = Path(d)
        save_architect_result(
            "owner",
            "repo",
            2,
            plan_hash_val,
            approved=False,
            block_reason="X",
            state_dir=state_dir,
        )
        cached = find_cached_architect_result(
            "owner", "repo", 2, plan_hash_val, ttl_hours=24.0, state_dir=state_dir
        )
        assert cached is not None
        assert cached.approved is False
        assert cached.block_reason == "X"
