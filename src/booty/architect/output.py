"""Architect output — ArchitectPlan and formatting for Builder handoff."""

from typing import Literal

from booty.planner.schema import HandoffToBuilder, Plan, Step

# Truncate architect_notes when long — first line inline, remainder in <details>
_NOTES_TRUNCATE_CHARS = 120


def format_architect_section(
    status: Literal["approved", "rewritten", "blocked"],
    risk_level: str | None = None,
    reason: str | None = None,
    architect_notes: str | None = None,
    rewrite_summary: list[str] | None = None,
) -> str:
    """Format booty-architect section for plan comment (ARCH-18).

    Approved: ✓ Approved — Risk: {risk_level}; optional architect_notes.
    Rewritten: ✎ Rewritten — {reason}; optional rewrite_summary, architect_notes.
    Blocked: Architect review required — plan is structurally unsafe. (reason)
    """
    lines: list[str] = []
    if status == "approved":
        risk = risk_level or "N/A"
        lines.append(f"✓ Approved — Risk: {risk}")
        if architect_notes:
            if len(architect_notes) <= _NOTES_TRUNCATE_CHARS and "\n" not in architect_notes:
                lines.append(architect_notes)
            else:
                first = architect_notes.split("\n")[0]
                if len(first) > _NOTES_TRUNCATE_CHARS:
                    first = first[: _NOTES_TRUNCATE_CHARS - 3] + "..."
                lines.append(first)
                lines.append("<details><summary>Notes</summary>\n\n" + architect_notes + "\n\n</details>")
    elif status == "rewritten":
        reason_text = reason or "ambiguous steps clarified"
        lines.append(f"✎ Rewritten — {reason_text}")
        if rewrite_summary:
            for item in rewrite_summary:
                lines.append(f"- {item}")
        if architect_notes:
            if len(architect_notes) <= _NOTES_TRUNCATE_CHARS and "\n" not in architect_notes:
                lines.append(architect_notes)
            else:
                first = architect_notes.split("\n")[0]
                if len(first) > _NOTES_TRUNCATE_CHARS:
                    first = first[: _NOTES_TRUNCATE_CHARS - 3] + "..."
                lines.append(first)
                lines.append("<details><summary>Notes</summary>\n\n" + architect_notes + "\n\n</details>")
    else:  # blocked
        lines.append("**Architect review required — plan is structurally unsafe.**")
        if reason:
            lines.append(f"({reason})")

    content = "\n\n".join(lines)
    return f"<!-- booty-architect -->\n{content}\n<!-- /booty-architect -->"


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
