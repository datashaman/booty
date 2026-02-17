"""Tests for architect rewrite (ambiguity, overreach)."""

import pytest

from booty.planner.schema import HandoffToBuilder, Plan, Step
from booty.architect.config import ArchitectConfig
from booty.architect.validation import derive_touch_paths
from booty.architect.rewrite import (
    check_ambiguity,
    check_overreach,
    rewrite_ambiguous_steps,
    try_rewrite_overreach,
)


def _plan(steps: list[Step], goal: str = "Test goal") -> Plan:
    handoff = HandoffToBuilder(
        branch_name_hint="b",
        commit_message_hint="c",
        pr_title="t",
        pr_body_outline="o",
    )
    p = Plan(goal=goal, steps=steps, handoff_to_builder=handoff)
    return p.model_copy(update={"touch_paths": derive_touch_paths(p)})


# --- ambiguity ---


def test_ambiguity_detects_short_acceptance() -> None:
    """check_ambiguity flags acceptance < 15 chars."""
    steps = [
        Step(id="P1", action="read", path="a.py", acceptance="Fix it"),
    ]
    plan = _plan(steps)
    got = check_ambiguity(plan)
    assert len(got) == 1
    assert got[0][0] == 0
    assert "short" in got[0][1].lower()


def test_ambiguity_detects_vague_pattern() -> None:
    """check_ambiguity flags vague patterns like 'fix' or 'improve'."""
    steps = [
        Step(id="P1", action="edit", path="a.py", acceptance="Fix the bug and improve as needed"),
    ]
    plan = _plan(steps)
    got = check_ambiguity(plan)
    assert len(got) >= 1


def test_ambiguity_passes_specific_acceptance() -> None:
    """check_ambiguity passes when acceptance is specific enough."""
    steps = [
        Step(id="P1", action="edit", path="a.py", acceptance="Add input validation and unit tests"),
    ]
    plan = _plan(steps)
    got = check_ambiguity(plan)
    assert len(got) == 0


def test_rewrite_ambiguous_disabled_returns_flags() -> None:
    """rewrite_ambiguous_steps when disabled returns flags, does not modify."""
    steps = [
        Step(id="P1", action="read", path="a.py", acceptance="Fix it"),
    ]
    plan = _plan(steps)
    config = ArchitectConfig(rewrite_ambiguous_steps=False)
    out_plan, notes = rewrite_ambiguous_steps(plan, config)
    assert out_plan is plan
    assert len(notes) >= 1
    assert "ambiguous" in notes[0].lower()


def test_rewrite_ambiguous_enabled_tightens() -> None:
    """rewrite_ambiguous_steps when enabled can tighten acceptance."""
    steps = [
        Step(id="P1", action="read", path="a.py", acceptance="Fix it"),
    ]
    plan = _plan(steps)
    config = ArchitectConfig(rewrite_ambiguous_steps=True)
    out_plan, notes = rewrite_ambiguous_steps(plan, config)
    assert out_plan.steps[0].acceptance != "Fix it" or notes


# --- overreach ---


def test_overreach_many_paths() -> None:
    """check_overreach flags repo-wide when path count >= 8."""
    steps = [
        Step(id=f"P{i}", action="edit", path=f"src/f{i}.py", acceptance="Update file")
        for i in range(8)
    ]
    plan = _plan(steps)
    got = check_overreach(plan)
    assert any("many paths" in r for r in got)


def test_overreach_multi_domain() -> None:
    """check_overreach flags when touching 2+ domains."""
    steps = [
        Step(id="P1", action="edit", path="src/a.py", acceptance="x" * 20),
        Step(id="P2", action="edit", path="tests/test_a.py", acceptance="y" * 20),
    ]
    plan = _plan(steps)
    got = check_overreach(plan)
    assert any("multi-domain" in r for r in got)


def test_overreach_speculative_goal() -> None:
    """check_overreach flags speculative keywords in goal."""
    steps = [
        Step(id="P1", action="edit", path="src/a.py", acceptance="Update as per plan"),
    ]
    plan = _plan(steps, goal="Refactor architecture for better structure")
    got = check_overreach(plan)
    assert any("speculative" in r for r in got)


def test_overreach_passes_narrow_scope() -> None:
    """check_overreach passes when scope is narrow."""
    steps = [
        Step(id="P1", action="edit", path="src/auth.py", acceptance="Add validation logic"),
        Step(id="P2", action="edit", path="src/auth.py", acceptance="Add unit tests"),
    ]
    plan = _plan(steps)
    got = check_overreach(plan)
    assert len(got) == 0


def test_try_rewrite_overreach_returns_plan_when_none() -> None:
    """try_rewrite_overreach returns (plan, []) when no overreach."""
    steps = [
        Step(id="P1", action="edit", path="src/a.py", acceptance="x" * 20),
    ]
    plan = _plan(steps)
    out, notes = try_rewrite_overreach(plan)
    assert out is plan
    assert notes == []


def test_try_rewrite_overreach_returns_none_when_unresolvable() -> None:
    """try_rewrite_overreach returns (None, reasons) when can't resolve."""
    steps = [
        Step(id=f"P{i}", action="edit", path=f"src/f{i}.py", acceptance="x" * 20)
        for i in range(9)
    ]
    plan = _plan(steps)
    out, reasons = try_rewrite_overreach(plan)
    assert out is None
    assert len(reasons) >= 1
