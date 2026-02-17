"""Magentic prompt for diff-based code review — quality evaluation only."""

from pydantic import BaseModel
from magentic import prompt

from booty.reviewer.schema import CategoryResult


class _ReviewLLMOutput(BaseModel):
    """LLM output — exactly 6 CategoryResult, one per category."""

    categories: list[CategoryResult]


@prompt(
    """You are a code review assistant that evaluates PR changes for engineering quality only.

Evaluate the unified diff and PR metadata below. Focus on:
- Maintainability: clarity, structure, ease of future changes
- Overengineering: unnecessary abstraction, complexity
- Duplication: copy-paste, repeated logic that could be abstracted
- Tests: adequate coverage, quality of test design
- Naming/API: clear names, sensible API surface
- Architectural drift: respects existing patterns, no unexpected layering

DO NOT evaluate: lint, formatting, style nitpicks. DO NOT re-run tests or lint.
Output is review-level only — no line-by-line annotations.

For each category, produce:
- grade: PASS (no issues), WARN (minor concerns), FAIL (significant problems)
- findings: up to 3 per category; each has summary, detail, paths (file paths), optional suggestion
- confidence: low/med/high

Categories in order: Overengineering, Architectural drift, Tests, Duplication, Maintainability, Naming/API.
Produce exactly 6 CategoryResult entries.

=== DIFF ===
{diff_truncated}

=== PR ===
Title: {pr_title}
Body: {pr_body}

=== FILES CHANGED ===
{file_list}

=== SHAS ===
Base: {base_sha}  Head: {head_sha}
""",
    max_retries=3,
)
def _review_diff_impl(
    diff_truncated: str,
    pr_title: str,
    pr_body: str,
    file_list: str,
    base_sha: str,
    head_sha: str,
) -> _ReviewLLMOutput:
    """LLM evaluates diff and returns 6 category grades. Internal — use run_review.

    Magentic @prompt decorator injects the implementation: the function body is a
    placeholder. The LLM is instructed to produce exactly 6 CategoryResult entries
    (Overengineering, Architectural drift, Tests, Duplication, Maintainability,
    Naming/API), each with grade (PASS/WARN/FAIL), findings (up to 3 per category
    with summary, detail, paths, optional suggestion), and confidence (low/med/high).
    """
    ...
