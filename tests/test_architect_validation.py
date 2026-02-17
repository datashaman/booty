"""Tests for architect validation (structural, paths, risk)."""

import pytest

from booty.planner.schema import HandoffToBuilder, Plan, Step
from booty.architect.validation import (
    VALID_ACTIONS,
    ValidationResult,
    compute_risk_from_touch_paths,
    derive_touch_paths,
    ensure_touch_paths_and_risk,
    validate_paths,
    validate_structural,
)


def _minimal_plan(
    steps: list[Step] | None = None,
    touch_paths: list[str] | None = None,
    risk_level: str = "LOW",
) -> Plan:
    """Build minimal valid Plan for testing."""
    if steps is None:
        steps = [
            Step(
                id="P1",
                action="read",
                path="src/auth.py",
                acceptance="Understand auth structure",
            ),
        ]
    handoff = HandoffToBuilder(
        branch_name_hint="issue-1",
        commit_message_hint="fix: x",
        pr_title="PR",
        pr_body_outline="Body",
    )
    p = Plan(goal="Test goal", steps=steps, handoff_to_builder=handoff)
    tp = touch_paths if touch_paths is not None else derive_touch_paths(p)
    return p.model_copy(update={"touch_paths": tp, "risk_level": risk_level})


# --- structural ---


def test_structural_valid_plan_accepted() -> None:
    """validate_structural accepts valid plan."""
    plan = _minimal_plan()
    r = validate_structural(plan)
    assert r.passed
    assert not r.blocks
    assert not r.errors


def test_structural_rejects_more_than_12_steps() -> None:
    """validate_structural blocks plan with > 12 steps."""
    plan_dict = {
        "plan_version": "1",
        "goal": "x",
        "steps": [
            {"id": f"P{i}", "action": "read", "path": f"f{i}.py", "acceptance": "x"}
            for i in range(1, 14)
        ],
        "handoff_to_builder": {
            "branch_name_hint": "b",
            "commit_message_hint": "c",
            "pr_title": "t",
            "pr_body_outline": "o",
        },
        "touch_paths": [f"f{i}.py" for i in range(1, 14)],
    }
    r = validate_structural(plan_dict)
    assert not r.passed
    assert r.blocks
    assert "Steps > 12" in r.errors


def test_structural_rejects_missing_id_or_action() -> None:
    """validate_structural blocks step missing id or action."""
    # Plan model requires id and action, so we test via dict
    plan_dict = {
        "plan_version": "1",
        "goal": "x",
        "steps": [
            {"id": "P1", "action": "read", "path": "a.py", "acceptance": "x"},
            {"id": "", "action": "edit", "path": "b.py", "acceptance": "y"},
        ],
        "handoff_to_builder": {
            "branch_name_hint": "b",
            "commit_message_hint": "c",
            "pr_title": "t",
            "pr_body_outline": "o",
        },
        "touch_paths": ["a.py", "b.py"],
    }
    r = validate_structural(plan_dict)
    assert not r.passed
    assert r.blocks


def test_structural_rejects_invalid_action() -> None:
    """validate_structural blocks invalid action."""
    plan_dict = {
        "plan_version": "1",
        "goal": "x",
        "steps": [
            {"id": "P1", "action": "delete", "path": "a.py", "acceptance": "x"},
        ],
        "handoff_to_builder": {
            "branch_name_hint": "b",
            "commit_message_hint": "c",
            "pr_title": "t",
            "pr_body_outline": "o",
        },
        "touch_paths": ["a.py"],
    }
    r = validate_structural(plan_dict)
    assert not r.passed
    assert r.blocks
    assert "invalid action" in str(r.errors).lower()


def test_structural_accepts_research_action() -> None:
    """validate_structural accepts research action."""
    steps = [
        Step(
            id="P1",
            action="research",
            path="docs/research.md",
            acceptance="Document findings",
        ),
    ]
    plan = _minimal_plan(steps=steps)
    r = validate_structural(plan)
    assert r.passed
    assert not r.blocks


def test_structural_dict_normalized_to_plan() -> None:
    """validate_structural normalizes dict to Plan."""
    plan_dict = {
        "plan_version": "1",
        "goal": "x",
        "steps": [
            {"id": "P1", "action": "read", "path": "a.py", "acceptance": "x"},
        ],
        "handoff_to_builder": {
            "branch_name_hint": "b",
            "commit_message_hint": "c",
            "pr_title": "t",
            "pr_body_outline": "o",
        },
        "touch_paths": ["a.py"],
    }
    r = validate_structural(plan_dict)
    assert r.passed


# --- path ---


def test_derive_touch_paths_union_of_path_actions() -> None:
    """derive_touch_paths returns sorted unique paths from read/edit/add/research."""
    plan = _minimal_plan(
        steps=[
            Step(id="P1", action="read", path="/src/a.py", acceptance="x"),
            Step(id="P2", action="edit", path="src/b.py", acceptance="y"),
            Step(id="P3", action="add", path="src/a.py", acceptance="z"),
            Step(id="P4", action="run", command="pytest", acceptance="ok"),
        ]
    )
    got = derive_touch_paths(plan)
    assert got == ["src/a.py", "src/b.py"]


def test_derive_touch_paths_includes_research() -> None:
    """derive_touch_paths includes research steps."""
    plan = _minimal_plan(
        steps=[
            Step(
                id="P1",
                action="research",
                path="docs/findings.md",
                acceptance="x",
            ),
        ]
    )
    got = derive_touch_paths(plan)
    assert "docs/findings.md" in got


def test_validate_paths_blocks_read_with_empty_path() -> None:
    """validate_paths blocks read/add/edit/research with empty path."""
    plan = _minimal_plan(
        steps=[
            Step(id="P1", action="read", path=None, acceptance="x"),
        ]
    )
    r = validate_paths(plan)
    assert not r.passed
    assert r.blocks
    assert "path required" in str(r.errors).lower()


def test_validate_paths_accepts_run_verify_without_path() -> None:
    """validate_paths accepts run/verify with no path."""
    plan = _minimal_plan(
        steps=[
            Step(id="P1", action="run", command="pytest", acceptance="x"),
        ],
        touch_paths=[],
    )
    r = validate_paths(plan)
    assert r.passed
    assert not r.blocks


def test_validate_paths_flags_touch_paths_mismatch() -> None:
    """validate_paths flags touch_paths mismatch but does not block."""
    plan = _minimal_plan(
        steps=[
            Step(id="P1", action="read", path="src/a.py", acceptance="x"),
        ],
        touch_paths=["wrong.py"],
    )
    r = validate_paths(plan)
    assert r.passed
    assert not r.blocks
    assert r.flags
    assert any("mismatch" in f for f in r.flags)


# --- risk ---


def test_compute_risk_high_workflows() -> None:
    """compute_risk_from_touch_paths returns HIGH for .github/workflows."""
    assert compute_risk_from_touch_paths([".github/workflows/ci.yml"]) == "HIGH"


def test_compute_risk_high_lockfile() -> None:
    """compute_risk_from_touch_paths returns HIGH for lockfiles."""
    assert compute_risk_from_touch_paths(["package-lock.json"]) == "HIGH"
    assert compute_risk_from_touch_paths(["uv.lock"]) == "HIGH"


def test_compute_risk_medium_manifest() -> None:
    """compute_risk_from_touch_paths returns MEDIUM for manifests."""
    assert compute_risk_from_touch_paths(["pyproject.toml"]) == "MEDIUM"
    assert compute_risk_from_touch_paths(["src/package.json"]) == "MEDIUM"


def test_compute_risk_low_else() -> None:
    """compute_risk_from_touch_paths returns LOW for typical source."""
    assert compute_risk_from_touch_paths(["src/auth.py"]) == "LOW"


def test_ensure_touch_paths_and_risk_updates_plan() -> None:
    """ensure_touch_paths_and_risk recomputes touch_paths and risk."""
    plan = _minimal_plan(
        steps=[
            Step(id="P1", action="edit", path="pyproject.toml", acceptance="x"),
        ],
        touch_paths=["wrong.py"],
        risk_level="LOW",
    )
    out = ensure_touch_paths_and_risk(plan)
    assert out.touch_paths == ["pyproject.toml"]
    assert out.risk_level == "MEDIUM"


def test_ensure_touch_paths_overrides_planner_risk() -> None:
    """ensure_touch_paths_and_risk overrides when Planner risk differs."""
    plan = _minimal_plan(
        steps=[
            Step(id="P1", action="edit", path=".github/workflows/ci.yml", acceptance="x"),
        ],
        touch_paths=[".github/workflows/ci.yml"],
        risk_level="LOW",
    )
    out = ensure_touch_paths_and_risk(plan)
    assert out.risk_level == "HIGH"
