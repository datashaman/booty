"""Tests for planner generation — derive_touch_paths and generate_plan."""

from unittest.mock import patch

import pytest

from booty.planner.generation import derive_touch_paths, generate_plan
from booty.planner.input import PlannerInput
from booty.planner.schema import HandoffToBuilder, Plan, Step


class TestDeriveTouchPaths:
    """Tests for derive_touch_paths."""

    def test_empty_steps_returns_empty(self):
        assert derive_touch_paths([]) == []

    def test_only_run_verify_returns_empty(self):
        steps = [
            Step(id="P1", action="run", command="pytest", acceptance="pass"),
            Step(id="P2", action="verify", command="curl ...", acceptance="ok"),
        ]
        assert derive_touch_paths(steps) == []

    def test_read_edit_add_paths_extracted(self):
        steps = [
            Step(id="P1", action="read", path="src/foo.py", acceptance="ok"),
            Step(id="P2", action="edit", path="src/bar.py", acceptance="ok"),
            Step(id="P3", action="add", path="tests/test_foo.py", acceptance="ok"),
        ]
        assert derive_touch_paths(steps) == [
            "src/bar.py",
            "src/foo.py",
            "tests/test_foo.py",
        ]

    def test_mix_extracts_only_read_edit_add(self):
        steps = [
            Step(id="P1", action="read", path="src/foo.py", acceptance="ok"),
            Step(id="P2", action="run", command="pytest", acceptance="pass"),
            Step(id="P3", action="edit", path="tests/test_foo.py", acceptance="ok"),
        ]
        assert derive_touch_paths(steps) == ["src/foo.py", "tests/test_foo.py"]

    def test_leading_slash_normalized(self):
        steps = [
            Step(id="P1", action="read", path="/src/foo.py", acceptance="ok"),
        ]
        assert derive_touch_paths(steps) == ["src/foo.py"]

    def test_deduplication(self):
        steps = [
            Step(id="P1", action="read", path="src/foo.py", acceptance="ok"),
            Step(id="P2", action="edit", path="src/foo.py", acceptance="ok"),
        ]
        assert derive_touch_paths(steps) == ["src/foo.py"]


def _mock_plan() -> Plan:
    """Valid Plan for mocking LLM output."""
    return Plan(
        plan_version="1",
        goal="Add auth validation",
        steps=[
            Step(id="P1", action="read", path="src/auth.py", acceptance="File inspected"),
            Step(id="P2", action="edit", path="src/auth.py", acceptance="Validation added"),
            Step(id="P3", action="run", command="pytest tests/test_auth.py", acceptance="Tests pass"),
        ],
        risk_level="LOW",
        touch_paths=["src/auth.py"],  # Will be overwritten by derive_touch_paths
        handoff_to_builder=HandoffToBuilder(
            branch_name_hint="issue-1-add-auth",
            commit_message_hint="fix: add auth validation",
            pr_title="[#1] Add auth validation",
            pr_body_outline="- Add validation to login",
        ),
    )


class TestGeneratePlan:
    """Tests for generate_plan (mocked LLM for CI)."""

    @pytest.fixture
    def minimal_input(self):
        return PlannerInput(goal="Add auth validation", body="Add validation to login")

    def test_generate_plan_returns_plan(self, minimal_input):
        with patch("booty.planner.generation._generate_plan_impl", return_value=_mock_plan()):
            plan = generate_plan(minimal_input)
        assert plan is not None
        assert hasattr(plan, "steps")
        assert hasattr(plan, "touch_paths")
        assert hasattr(plan, "handoff_to_builder")

    def test_plan_steps_valid_ids_and_actions(self, minimal_input):
        with patch("booty.planner.generation._generate_plan_impl", return_value=_mock_plan()):
            plan = generate_plan(minimal_input)
        valid_actions = {"read", "edit", "add", "run", "verify"}
        for step in plan.steps:
            assert step.id.startswith("P") and step.id[1:].isdigit()
            assert step.action in valid_actions

    def test_touch_paths_derived_from_steps(self, minimal_input):
        with patch("booty.planner.generation._generate_plan_impl", return_value=_mock_plan()):
            plan = generate_plan(minimal_input)
        expected = derive_touch_paths(plan.steps)
        assert plan.touch_paths == expected

    def test_handoff_populated(self, minimal_input):
        with patch("booty.planner.generation._generate_plan_impl", return_value=_mock_plan()):
            plan = generate_plan(minimal_input)
        h = plan.handoff_to_builder
        assert h.branch_name_hint
        assert h.commit_message_hint
        assert h.pr_title
        assert h.pr_body_outline is not None
