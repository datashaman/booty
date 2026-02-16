"""Tests for plan comment formatting."""

import pytest

from booty.planner.output import format_plan_comment
from booty.planner.schema import HandoffToBuilder, Plan, Step


def test_format_plan_comment_includes_sections() -> None:
    """Output includes Goal, Risk, Steps, Builder instructions."""
    plan = Plan(
        goal="Add auth validation",
        steps=[
            Step(id="P1", action="read", path="src/auth.py", acceptance="inspected"),
            Step(id="P2", action="edit", path="src/auth.py", acceptance="validation added"),
        ],
        handoff_to_builder=HandoffToBuilder(
            branch_name_hint="issue-1-auth",
            commit_message_hint="fix: add auth validation",
            pr_title="[#1] Add auth",
            pr_body_outline="Summary of changes",
        ),
    )
    out = format_plan_comment(plan)
    assert "## Goal" in out
    assert "## Risk" in out
    assert "## Steps" in out
    assert "## Builder instructions" in out
    assert "Add auth validation" in out


def test_format_plan_comment_includes_marker() -> None:
    """Output ends with booty-plan marker."""
    plan = Plan(
        goal="Test",
        steps=[Step(id="P1", action="read", path="x", acceptance="done")],
        handoff_to_builder=HandoffToBuilder(
            branch_name_hint="b",
            commit_message_hint="c",
            pr_title="t",
            pr_body_outline="out",
        ),
    )
    out = format_plan_comment(plan)
    assert "<!-- booty-plan -->" in out


def test_format_plan_comment_omits_empty_handoff() -> None:
    """Empty handoff fields omitted; partial handoff produces only populated bullets."""
    plan = Plan(
        goal="Test",
        steps=[Step(id="P1", action="read", path="x", acceptance="done")],
        handoff_to_builder=HandoffToBuilder(
            branch_name_hint="issue-5-foo",
            commit_message_hint="",
            pr_title="",
            pr_body_outline="",
        ),
    )
    out = format_plan_comment(plan)
    assert "**Branch:** issue-5-foo" in out
    assert "**Commit:**" not in out
    assert "**PR Title:**" not in out
    assert "**PR Body:**" not in out


def test_format_plan_comment_pr_body_long_collapsed() -> None:
    """Long pr_body_outline (>200 chars) rendered in collapsed details."""
    long_body = "A" * 250
    plan = Plan(
        goal="Test",
        steps=[],
        handoff_to_builder=HandoffToBuilder(
            branch_name_hint="b",
            commit_message_hint="c",
            pr_title="t",
            pr_body_outline=long_body,
        ),
    )
    out = format_plan_comment(plan)
    assert "<details>" in out
    assert "PR body outline" in out
    assert long_body in out
