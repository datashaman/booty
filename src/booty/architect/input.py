"""Architect input — plan, normalized input, optional repo context."""

from booty.planner.input import PlannerInput
from booty.planner.schema import Plan


class ArchitectInput:
    """Input for Architect Agent (plan, normalized_input, optional repo_context, issue_metadata)."""

    def __init__(
        self,
        plan: Plan | dict,
        normalized_input: PlannerInput,
        repo_context: dict | None = None,
        issue_metadata: dict | None = None,
    ) -> None:
        self.plan = plan
        self.normalized_input = normalized_input
        self.repo_context = repo_context
        self.issue_metadata = issue_metadata
