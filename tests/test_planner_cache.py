"""Tests for planner cache primitives."""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from booty.planner.cache import (
    find_cached_ad_hoc_plan,
    find_cached_issue_plan,
    input_hash,
    is_plan_fresh,
    plan_hash,
    save_ad_hoc_plan,
)
from booty.planner.input import PlannerInput
from booty.planner.schema import HandoffToBuilder, Plan, Step
from booty.planner.store import load_plan, plan_path_for_issue, save_plan


def test_input_hash_deterministic() -> None:
    """Same PlannerInput yields same hash; sorted labels don't affect."""
    inp1 = PlannerInput(goal="x", body="y", labels=["a", "b"])
    inp2 = PlannerInput(goal="x", body="y", labels=["b", "a"])
    h1 = input_hash(inp1)
    h2 = input_hash(inp2)
    assert h1 == h2
    assert len(h1) == 64


def test_input_hash_excludes_metadata() -> None:
    """Metadata changes don't affect input_hash."""
    inp1 = PlannerInput(goal="x", body="y", labels=[], metadata={"issue_url": "a"})
    inp2 = PlannerInput(goal="x", body="y", labels=[], metadata={"issue_url": "b"})
    assert input_hash(inp1) == input_hash(inp2)


def test_plan_hash_excludes_metadata() -> None:
    """plan_hash ignores metadata, created_at."""
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
    assert plan_hash(p1) == plan_hash(p2)
    assert len(plan_hash(p1)) == 64


def test_load_plan_missing_returns_none() -> None:
    """load_plan returns None when file doesn't exist."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "missing.json"
        assert load_plan(path) is None


def test_load_plan_invalid_returns_none() -> None:
    """load_plan returns None for invalid JSON or invalid schema."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "invalid.json"
        path.write_text("not json")
        assert load_plan(path) is None
        path.write_text('{"goal": "x"}')  # missing required handoff_to_builder
        assert load_plan(path) is None


def test_find_cached_issue_plan_hit() -> None:
    """Stored plan with matching input_hash and fresh returns plan."""
    handoff = HandoffToBuilder(
        branch_name_hint="b", commit_message_hint="c", pr_title="t", pr_body_outline="o"
    )
    plan = Plan(
        goal="g",
        steps=[Step(id="P1", action="read", path="x", acceptance="d")],
        handoff_to_builder=handoff,
        metadata={
            "input_hash": "abc123",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    with tempfile.TemporaryDirectory() as d:
        os.environ["PLANNER_STATE_DIR"] = d
        try:
            path = plan_path_for_issue("o", "r", 1)
            path.parent.mkdir(parents=True, exist_ok=True)
            save_plan(plan, path)
            cached = find_cached_issue_plan("o", "r", 1, "abc123", 24.0)
            assert cached is not None
            assert cached.goal == "g"
        finally:
            os.environ.pop("PLANNER_STATE_DIR", None)


def test_find_cached_issue_plan_miss_input_hash() -> None:
    """find_cached_issue_plan returns None when input_hash doesn't match."""
    handoff = HandoffToBuilder(
        branch_name_hint="b", commit_message_hint="c", pr_title="t", pr_body_outline="o"
    )
    plan = Plan(
        goal="g",
        steps=[Step(id="P1", action="read", path="x", acceptance="d")],
        handoff_to_builder=handoff,
        metadata={
            "input_hash": "abc123",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    with tempfile.TemporaryDirectory() as d:
        os.environ["PLANNER_STATE_DIR"] = d
        try:
            path = plan_path_for_issue("o", "r", 1)
            path.parent.mkdir(parents=True, exist_ok=True)
            save_plan(plan, path)
            assert find_cached_issue_plan("o", "r", 1, "wrong_hash", 24.0) is None
        finally:
            os.environ.pop("PLANNER_STATE_DIR", None)


def test_find_cached_issue_plan_miss_expired() -> None:
    """find_cached_issue_plan returns None when plan is expired."""
    handoff = HandoffToBuilder(
        branch_name_hint="b", commit_message_hint="c", pr_title="t", pr_body_outline="o"
    )
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    plan = Plan(
        goal="g",
        steps=[Step(id="P1", action="read", path="x", acceptance="d")],
        handoff_to_builder=handoff,
        metadata={"input_hash": "abc123", "created_at": old_ts},
    )
    with tempfile.TemporaryDirectory() as d:
        os.environ["PLANNER_STATE_DIR"] = d
        try:
            path = plan_path_for_issue("o", "r", 1)
            path.parent.mkdir(parents=True, exist_ok=True)
            save_plan(plan, path)
            assert find_cached_issue_plan("o", "r", 1, "abc123", 24.0) is None
        finally:
            os.environ.pop("PLANNER_STATE_DIR", None)


def test_is_plan_fresh() -> None:
    """is_plan_fresh returns True within TTL, False after."""
    now = datetime.now(timezone.utc)
    assert is_plan_fresh(now, 24) is True
    assert is_plan_fresh(now - timedelta(hours=25), 24) is False


def test_find_cached_ad_hoc_plan_hit() -> None:
    """save via save_ad_hoc_plan, find returns plan."""
    handoff = HandoffToBuilder(
        branch_name_hint="b", commit_message_hint="c", pr_title="t", pr_body_outline="o"
    )
    plan = Plan(
        goal="g",
        steps=[Step(id="P1", action="read", path="x", acceptance="d")],
        handoff_to_builder=handoff,
        metadata={
            "input_hash": "abc123",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    inp = PlannerInput(goal="x", body="y", labels=[])
    with tempfile.TemporaryDirectory() as d:
        os.environ["PLANNER_STATE_DIR"] = d
        try:
            path = save_ad_hoc_plan(plan, inp)
            assert path.exists()
            cached = find_cached_ad_hoc_plan(input_hash(inp), 24.0)
            assert cached is not None
            assert cached.goal == "g"
        finally:
            os.environ.pop("PLANNER_STATE_DIR", None)


def test_find_cached_ad_hoc_plan_miss_hash() -> None:
    """find_cached_ad_hoc_plan returns None when input_hash doesn't match."""
    handoff = HandoffToBuilder(
        branch_name_hint="b", commit_message_hint="c", pr_title="t", pr_body_outline="o"
    )
    plan = Plan(
        goal="g",
        steps=[Step(id="P1", action="read", path="x", acceptance="d")],
        handoff_to_builder=handoff,
        metadata={
            "input_hash": "abc123",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    inp = PlannerInput(goal="x", body="y", labels=[])
    with tempfile.TemporaryDirectory() as d:
        os.environ["PLANNER_STATE_DIR"] = d
        try:
            save_ad_hoc_plan(plan, inp)
            assert find_cached_ad_hoc_plan("wrong_hash", 24.0) is None
        finally:
            os.environ.pop("PLANNER_STATE_DIR", None)


def test_find_cached_ad_hoc_plan_miss_expired() -> None:
    """find_cached_ad_hoc_plan returns None when plan is expired."""
    handoff = HandoffToBuilder(
        branch_name_hint="b", commit_message_hint="c", pr_title="t", pr_body_outline="o"
    )
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    plan = Plan(
        goal="g",
        steps=[Step(id="P1", action="read", path="x", acceptance="d")],
        handoff_to_builder=handoff,
        metadata={"input_hash": "abc123", "created_at": old_ts},
    )
    inp = PlannerInput(goal="x", body="y", labels=[])
    with tempfile.TemporaryDirectory() as d:
        os.environ["PLANNER_STATE_DIR"] = d
        try:
            save_ad_hoc_plan(plan, inp)
            assert find_cached_ad_hoc_plan(input_hash(inp), 24.0) is None
        finally:
            os.environ.pop("PLANNER_STATE_DIR", None)


def test_ad_hoc_preserves_history() -> None:
    """Two saves with same input produce two files; index points to latest."""
    handoff = HandoffToBuilder(
        branch_name_hint="b", commit_message_hint="c", pr_title="t", pr_body_outline="o"
    )
    inp = PlannerInput(goal="x", body="y", labels=[])
    plan1 = Plan(
        goal="g1",
        steps=[Step(id="P1", action="read", path="x", acceptance="d")],
        handoff_to_builder=handoff,
        metadata={"created_at": datetime.now(timezone.utc).isoformat()},
    )
    plan2 = Plan(
        goal="g2",
        steps=[Step(id="P1", action="edit", path="x", acceptance="d")],
        handoff_to_builder=handoff,
        metadata={"created_at": datetime.now(timezone.utc).isoformat()},
    )
    with tempfile.TemporaryDirectory() as d:
        os.environ["PLANNER_STATE_DIR"] = d
        try:
            path1 = save_ad_hoc_plan(plan1, inp)
            path2 = save_ad_hoc_plan(plan2, inp)
            assert path1 != path2
            assert path1.exists()
            assert path2.exists()
            cached = find_cached_ad_hoc_plan(input_hash(inp), 24.0)
            assert cached is not None
            assert cached.goal == "g2"
        finally:
            os.environ.pop("PLANNER_STATE_DIR", None)
