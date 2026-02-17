"""Architect worker — process plans, return approval status."""

from pydantic import ValidationError

from booty.architect.config import ArchitectConfig
from booty.architect.input import ArchitectInput
from booty.architect.rewrite import check_overreach, rewrite_ambiguous_steps, try_rewrite_overreach
from booty.architect.validation import (
    ensure_touch_paths_and_risk,
    validate_paths,
    validate_structural,
)
from booty.planner.schema import Plan


class ArchitectResult:
    """Result of Architect processing (approved, plan, optional notes)."""

    def __init__(
        self,
        approved: bool,
        plan: object,
        architect_notes: str | None = None,
    ) -> None:
        self.approved = approved
        self.plan = plan
        self.architect_notes = architect_notes


def _block(reason: str, plan: object) -> ArchitectResult:
    """Return blocked result with fixed message plus reason."""
    msg = "Architect review required — plan is structurally unsafe."
    if reason:
        msg = f"{msg} ({reason})"
    return ArchitectResult(approved=False, plan=plan, architect_notes=msg)


def process_architect_input(config: ArchitectConfig, inp: ArchitectInput) -> ArchitectResult:
    """Process Architect input with full validation pipeline.

    Pipeline: normalize → structural → paths → ensure_touch_paths_and_risk →
    rewrite_ambiguous → check_overreach/try_rewrite_overreach.
    On block: return approved=False with fixed message. Retry validation once after rewrite.
    Architect operates when repo_context is None (ARCH-05).
    """
    plan_raw = inp.plan

    # Normalize to Plan
    try:
        plan = Plan.model_validate(plan_raw) if isinstance(plan_raw, dict) else plan_raw
    except ValidationError:
        return _block("Invalid plan structure", plan_raw)

    if not isinstance(plan, Plan):
        return _block("Invalid plan structure", plan_raw)

    notes: list[str] = []

    def run_validation(plan_to_check: Plan) -> ArchitectResult | None:
        """Run structural and path validation. Return ArchitectResult on block, None to continue."""
        r_struct = validate_structural(plan_to_check)
        if r_struct.blocks:
            return _block(r_struct.errors[0] if r_struct.errors else "Structural validation failed", plan_raw)
        r_paths = validate_paths(plan_to_check)
        if r_paths.blocks:
            return _block(
                r_paths.errors[0] if r_paths.errors else "Path validation failed",
                plan_raw,
            )
        if r_paths.flags:
            notes.extend(r_paths.flags)
        return None

    blocked = run_validation(plan)
    if blocked:
        return blocked

    plan = ensure_touch_paths_and_risk(plan)

    plan, ambig_notes = rewrite_ambiguous_steps(plan, config)
    notes.extend(ambig_notes)

    overreach_reasons = check_overreach(plan)
    if overreach_reasons:
        rewritten, rewrite_notes = try_rewrite_overreach(plan)
        if rewritten is not None:
            plan = rewritten
            notes.extend(rewrite_notes)
        else:
            return _block(overreach_reasons[0], plan_raw)

    # Retry validation once after rewrites (CONTEXT: one additional attempt)
    blocked = run_validation(plan)
    if blocked:
        return blocked

    notes_text = "; ".join(notes) if notes else None
    return ArchitectResult(approved=True, plan=plan, architect_notes=notes_text)
