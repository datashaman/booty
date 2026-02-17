"""Tests for architect worker (validation pipeline, block flow, performance)."""

import time

import pytest

from booty.planner.schema import HandoffToBuilder, Plan, Step
from booty.planner.input import PlannerInput
from booty.architect.config import ArchitectConfig
from booty.architect.input import ArchitectInput
from booty.architect.worker import process_architect_input


def _minimal_plan(steps: list[Step] | None = None) -> Plan:
    if steps is None:
        steps = [
            Step(id="P1", action="read", path="src/auth.py", acceptance="Understand auth structure"),
            Step(id="P2", action="edit", path="src/auth.py", acceptance="Add validation and tests"),
        ]
    handoff = HandoffToBuilder(
        branch_name_hint="issue-1",
        commit_message_hint="fix: auth",
        pr_title="PR",
        pr_body_outline="Body",
    )
    return Plan(goal="Add auth validation", steps=steps, handoff_to_builder=handoff)


def _architect_input(plan: Plan | dict):
    return ArchitectInput(
        plan=plan,
        normalized_input=PlannerInput(goal="x", body=""),
        repo_context=None,
    )


def test_process_architect_input_valid_plan_returns_approved() -> None:
    """process_architect_input with valid plan returns approved."""
    plan = _minimal_plan()
    config = ArchitectConfig(enabled=True)
    inp = _architect_input(plan)
    r = process_architect_input(config, inp)
    assert r.approved is True
    assert r.plan is not None


def test_process_architect_input_more_than_12_steps_returns_blocked() -> None:
    """process_architect_input with >12 steps returns blocked."""
    steps = [
        Step(id=f"P{i}", action="read", path=f"f{i}.py", acceptance="x" * 20)
        for i in range(1, 14)
    ]
    plan_dict = {
        "plan_version": "1",
        "goal": "x",
        "steps": [{"id": s.id, "action": s.action, "path": s.path, "acceptance": s.acceptance} for s in steps],
        "handoff_to_builder": {
            "branch_name_hint": "b",
            "commit_message_hint": "c",
            "pr_title": "t",
            "pr_body_outline": "o",
        },
        "touch_paths": [f"f{i}.py" for i in range(1, 14)],
    }
    config = ArchitectConfig(enabled=True)
    inp = _architect_input(plan_dict)
    r = process_architect_input(config, inp)
    assert r.approved is False
    assert "structurally unsafe" in (r.architect_notes or "")


def test_process_architect_input_invalid_action_returns_blocked() -> None:
    """process_architect_input with invalid action returns blocked."""
    plan_dict = {
        "plan_version": "1",
        "goal": "x",
        "steps": [
            {"id": "P1", "action": "delete", "path": "a.py", "acceptance": "x" * 20},
        ],
        "handoff_to_builder": {
            "branch_name_hint": "b",
            "commit_message_hint": "c",
            "pr_title": "t",
            "pr_body_outline": "o",
        },
        "touch_paths": ["a.py"],
    }
    config = ArchitectConfig(enabled=True)
    inp = _architect_input(plan_dict)
    r = process_architect_input(config, inp)
    assert r.approved is False


def test_process_architect_input_completes_under_5_seconds() -> None:
    """process_architect_input completes in < 5 seconds for typical plan."""
    steps = [
        Step(id=f"P{i}", action="read", path=f"src/f{i}.py", acceptance="Step acceptance criteria here")
        for i in range(5)
    ]
    plan = _minimal_plan(steps=steps)
    config = ArchitectConfig(enabled=True)
    inp = _architect_input(plan)
    start = time.perf_counter()
    r = process_architect_input(config, inp)
    elapsed = time.perf_counter() - start
    assert r.approved is True
    assert elapsed < 5.0, f"process_architect_input took {elapsed:.2f}s, expected < 5s"
