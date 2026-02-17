"""Plan comment formatting for GitHub issue posting."""

import json

from booty.planner.schema import HandoffToBuilder, Plan, Step


def _step_line(step: Step) -> str:
    """Format single step as bullet line."""
    if step.action in ("read", "edit", "add"):
        action_path = f"{step.action} {step.path}" if step.path else step.action
    elif step.action in ("run", "verify"):
        action_path = step.command or step.action
    else:
        action_path = step.path or step.action
    return f"- {step.id}: {action_path} — {step.acceptance}"


def _builder_bullets(handoff: HandoffToBuilder) -> list[str]:
    """Builder instructions bullets; omit empty fields."""
    bullets = []
    if handoff.branch_name_hint.strip():
        bullets.append(f"- **Branch:** {handoff.branch_name_hint}")
    if handoff.commit_message_hint.strip():
        bullets.append(f"- **Commit:** {handoff.commit_message_hint}")
    if handoff.pr_title.strip():
        bullets.append(f"- **PR Title:** {handoff.pr_title}")
    if handoff.pr_body_outline.strip():
        body = handoff.pr_body_outline
        if len(body) <= 200 and body.count("\n") <= 1:
            bullets.append(f"- **PR Body:** {body}")
        else:
            bullets.append(
                "- **PR Body:**\n<details><summary>PR body outline</summary>\n\n"
                f"{body}\n\n</details>"
            )
    return bullets


def format_plan_comment(plan: Plan, architect_section: str | None = None) -> str:
    """Format plan as markdown for GitHub issue comment.

    Sections: Goal, Risk, Steps, Builder instructions, optional booty-architect section, collapsed JSON.
    architect_section: when provided, inserted between Builder instructions and <details>.
    Ends with <!-- booty-plan --> for find-and-edit.
    """
    sections = []

    sections.append("## Goal\n\n" + plan.goal)
    sections.append("## Risk\n\n" + plan.risk_level)
    sections.append(
        "## Steps\n\n" + "\n".join(_step_line(s) for s in plan.steps)
    )

    bullets = _builder_bullets(plan.handoff_to_builder)
    if bullets:
        sections.append("## Builder instructions\n\n" + "\n".join(bullets))

    if architect_section:
        sections.append(architect_section)

    raw_json = json.dumps(
        plan.model_dump(),
        indent=2,
        default=str,
    )
    sections.append(
        "<details><summary>Full plan (JSON)</summary>\n\n```json\n"
        f"{raw_json}\n```\n\n</details>"
    )

    return "\n\n".join(sections) + "\n\n<!-- booty-plan -->"
