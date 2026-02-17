"""Plan JSON schema (Pydantic) for Planner Agent."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Step(BaseModel):
    """Single step in a plan."""

    id: str = Field(
        ...,
        pattern=r"^P\d+$",
        description="Step identifier P1, P2, ... P12 (exactly this format)",
    )
    action: Literal["read", "edit", "add", "run", "verify", "research"] = Field(
        description="One of: read (inspect file), edit (modify existing), add (create new), run (execute command), verify (check outcome)"
    )
    path: str | None = Field(
        default=None,
        description="File path for read/edit/add; None for run/verify",
    )
    command: str | None = Field(
        default=None,
        description="Shell command for run/verify; None for read/edit/add",
    )
    acceptance: str = Field(
        description="How to verify this step is done (specific, measurable)"
    )


class HandoffToBuilder(BaseModel):
    """Handoff metadata for Builder agent."""

    branch_name_hint: str = Field(
        description="Conventional format e.g. issue-123-short-slug"
    )
    commit_message_hint: str = Field(
        description="Conventional commit e.g. fix: add auth validation"
    )
    pr_title: str = Field(
        description="PR title, include issue ref when available e.g. [#123] Add validation"
    )
    pr_body_outline: str = Field(
        description="Bullets for technical items, short prose for context"
    )


class Plan(BaseModel):
    """Plan JSON schema v1."""

    model_config = ConfigDict(extra="forbid")

    plan_version: Literal["1"] = "1"
    goal: str
    steps: list[Step] = Field(default_factory=list, max_length=12)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    touch_paths: list[str] = Field(default_factory=list)
    handoff_to_builder: HandoffToBuilder
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    rollback: list[str] = Field(default_factory=list)
    metadata: dict = Field(
        default_factory=dict,
        description="Run metadata: created_at, input_hash, plan_hash (excluded from plan_hash)",
    )
