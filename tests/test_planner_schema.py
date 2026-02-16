"""Tests for planner schema and store."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from booty.planner import Plan, Step, HandoffToBuilder
from booty.planner.store import (
    get_planner_state_dir,
    plan_path_for_ad_hoc,
    plan_path_for_issue,
    save_plan,
)


def test_plan_validation_accepts_valid_dict() -> None:
    """Plan.model_validate accepts valid dict."""
    d = {
        "plan_version": "1",
        "goal": "Add feature",
        "steps": [
            {"id": "P1", "action": "add", "path": "src/foo.py", "command": None, "acceptance": "File exists"}
        ],
        "risk_level": "LOW",
        "touch_paths": ["src/foo.py"],
        "handoff_to_builder": {
            "branch_name_hint": "feat/foo",
            "commit_message_hint": "Add foo",
            "pr_title": "Add foo",
            "pr_body_outline": "Implements foo",
        },
    }
    p = Plan.model_validate(d)
    assert p.plan_version == "1"
    assert p.goal == "Add feature"
    assert len(p.steps) == 1
    assert p.steps[0].id == "P1"


def test_plan_rejects_invalid_plan_version() -> None:
    """Plan rejects invalid plan_version."""
    d = {
        "plan_version": "2",
        "goal": "Add feature",
        "steps": [],
        "risk_level": "LOW",
        "touch_paths": [],
        "handoff_to_builder": {
            "branch_name_hint": "feat",
            "commit_message_hint": "Add",
            "pr_title": "Add",
            "pr_body_outline": "",
        },
    }
    with pytest.raises(ValueError):
        Plan.model_validate(d)


def test_plan_rejects_more_than_12_steps() -> None:
    """Plan rejects >12 steps."""
    handoff = HandoffToBuilder(
        branch_name_hint="feat",
        commit_message_hint="Add",
        pr_title="Add",
        pr_body_outline="",
    )
    steps = [
        Step(id=f"P{i}", action="add", path=f"src/p{i}.py", command=None, acceptance="Done")
        for i in range(1, 14)
    ]
    with pytest.raises(ValueError):
        Plan(goal="Many steps", steps=steps, risk_level="LOW", touch_paths=[], handoff_to_builder=handoff)


def test_step_rejects_invalid_action() -> None:
    """Step rejects invalid action."""
    with pytest.raises(ValueError):
        Step(id="P1", action="research", path=None, command=None, acceptance="Done")


def test_get_planner_state_dir_uses_env() -> None:
    """get_planner_state_dir uses PLANNER_STATE_DIR."""
    with tempfile.TemporaryDirectory() as d:
        os.environ["PLANNER_STATE_DIR"] = d
        try:
            sd = get_planner_state_dir()
            assert str(sd) == d
        finally:
            os.environ.pop("PLANNER_STATE_DIR", None)


def test_plan_path_for_issue_produces_correct_path() -> None:
    """plan_path_for_issue produces correct nested path."""
    with tempfile.TemporaryDirectory() as d:
        sd = Path(d)
        p = plan_path_for_issue("owner", "repo", 42, sd)
        assert p == sd / "plans" / "owner" / "repo" / "42.json"


def test_plan_path_for_ad_hoc_produces_path() -> None:
    """plan_path_for_ad_hoc produces ad-hoc path."""
    with tempfile.TemporaryDirectory() as d:
        sd = Path(d)
        p = plan_path_for_ad_hoc("hello world", sd)
        assert "ad-hoc-" in p.name
        assert p.name.endswith(".json")


def test_save_plan_writes_valid_json() -> None:
    """save_plan writes valid JSON, readable back."""
    handoff = HandoffToBuilder(
        branch_name_hint="feat",
        commit_message_hint="Add",
        pr_title="Add",
        pr_body_outline="",
    )
    plan = Plan(goal="Test", steps=[], risk_level="LOW", touch_paths=[], handoff_to_builder=handoff)
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "plan.json"
        save_plan(plan, path)
        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded["goal"] == "Test"
        assert loaded["plan_version"] == "1"
