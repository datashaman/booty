"""Tests for Architect output — ArchitectPlan, build_architect_plan."""

import pytest

from booty.architect.output import ArchitectPlan, build_architect_plan
from booty.planner.schema import HandoffToBuilder, Plan, Step


@pytest.fixture
def sample_plan() -> Plan:
    return Plan(
        goal="Add auth validation",
        steps=[
            Step(id="P1", action="read", path="src/auth.py", acceptance="File inspected"),
            Step(id="P2", action="edit", path="src/auth.py", acceptance="Validation added"),
        ],
        handoff_to_builder=HandoffToBuilder(
            branch_name_hint="issue-42-auth",
            commit_message_hint="fix: add auth validation",
            pr_title="[#42] Add auth validation",
            pr_body_outline="- Add validation\n- Tests",
        ),
        touch_paths=["src/auth.py"],
        risk_level="MEDIUM",
    )


def test_build_architect_plan_maps_fields(sample_plan: Plan) -> None:
    """All Plan fields map to ArchitectPlan."""
    ap = build_architect_plan(sample_plan, "Clarified step P2 acceptance")
    assert ap.plan_version == "1"
    assert ap.goal == "Add auth validation"
    assert len(ap.steps) == 2
    assert ap.steps[0].id == "P1"
    assert ap.steps[1].id == "P2"
    assert ap.touch_paths == ["src/auth.py"]
    assert ap.risk_level == "MEDIUM"
    assert ap.handoff_to_builder.pr_title == "[#42] Add auth validation"
    assert ap.architect_notes == "Clarified step P2 acceptance"


def test_build_architect_plan_architect_notes_optional(sample_plan: Plan) -> None:
    """architect_notes is optional: with notes and without notes."""
    ap_with = build_architect_plan(sample_plan, "ambiguous steps clarified")
    assert ap_with.architect_notes == "ambiguous steps clarified"

    ap_without = build_architect_plan(sample_plan)
    assert ap_without.architect_notes is None
