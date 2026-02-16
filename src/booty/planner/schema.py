"""Plan JSON schema (Pydantic) for Planner Agent."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Step(BaseModel):
    """Single step in a plan."""

    id: str = Field(..., pattern=r"^P\d+$", description="Step id (P1..P12)")
    action: Literal["read", "edit", "add", "run", "verify"]
    path: str | None = None
    command: str | None = None
    acceptance: str


class HandoffToBuilder(BaseModel):
    """Handoff metadata for Builder agent."""

    branch_name_hint: str
    commit_message_hint: str
    pr_title: str
    pr_body_outline: str


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
