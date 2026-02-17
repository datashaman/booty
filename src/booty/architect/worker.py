"""Architect worker — process plans, return approval status."""

from booty.architect.config import ArchitectConfig
from booty.architect.input import ArchitectInput


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


def process_architect_input(config: ArchitectConfig, inp: ArchitectInput) -> ArchitectResult:
    """Process Architect input. Phase 32: pass-through (approved=True when config.enabled).

    Architect operates when repo_context is None (ARCH-05).
    Caller ensures process_architect_input is only called when config.enabled.
    """
    return ArchitectResult(approved=True, plan=inp.plan, architect_notes=None)
