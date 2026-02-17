"""Architect output — ArchitectPlan and formatting for Builder handoff."""

from typing import Literal

from booty.planner.schema import HandoffToBuilder, Plan, Step


class ArchitectPlan:
    """Structured output for Builder handoff and comment display (ARCH-16)."""

    def __init__(
        self,
        plan_version: str,
        goal: str,
        steps: list[Step],
        touch_paths: list[str],
        risk_level: Literal["LOW", "MEDIUM", "HIGH"],
        handoff_to_builder: HandoffToBuilder,
        architect_notes: str | None = None,
    ) -> None:
        self.plan_version = plan_version
        self.goal = goal
        self.steps = steps
        self.touch_paths = touch_paths
        self.risk_level = risk_level
        self.handoff_to_builder = handoff_to_builder
        self.architect_notes = architect_notes


def build_architect_plan(
    plan: Plan,
    architect_notes: str | None = None,
) -> ArchitectPlan:
    """Build ArchitectPlan from validated Plan.

    architect_notes optional per ARCH-17; not consumed by Builder.
    """
    return ArchitectPlan(
        plan_version=plan.plan_version,
        goal=plan.goal,
        steps=plan.steps,
        touch_paths=plan.touch_paths,
        risk_level=plan.risk_level,
        handoff_to_builder=plan.handoff_to_builder,
        architect_notes=architect_notes,
    )
