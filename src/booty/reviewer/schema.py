"""Review output schema — Pydantic models for LLM output and engine result."""

from typing import Literal

from pydantic import BaseModel, Field


ReviewDecision = Literal["APPROVED", "APPROVED_WITH_SUGGESTIONS", "BLOCKED"]
Grade = Literal["PASS", "WARN", "FAIL"]
Confidence = Literal["low", "med", "high"]

# Category names in evaluation order (per CONTEXT.md)
CATEGORY_ORDER = (
    "Overengineering",
    "Architectural drift",
    "Tests",
    "Duplication",
    "Maintainability",
    "Naming/API",
)


class Finding(BaseModel):
    """Single finding within a category."""

    summary: str
    detail: str
    paths: list[str] = Field(default_factory=list)
    line_refs: list[str] | None = None
    suggestion: str | None = None


class CategoryResult(BaseModel):
    """LLM output per evaluation category."""

    category: str  # Overengineering, Architectural drift, Tests, Duplication, Maintainability, Naming/API
    grade: Grade
    findings: list[Finding] = Field(default_factory=list)
    confidence: Confidence = "med"


class ReviewResult(BaseModel):
    """Engine output — decision, categories, rationale for BLOCKED."""

    decision: ReviewDecision
    categories: list[CategoryResult] = Field(default_factory=list)
    blocking_categories: list[str] = Field(
        default_factory=list,
        description="Categories that caused BLOCKED (for comment rationale)",
    )
