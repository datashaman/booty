"""Review engine — run_review, block_on mapping, decision logic."""

from typing import Literal

from booty.reviewer.prompts import _review_diff_impl
from booty.reviewer.schema import (
    CATEGORY_ORDER,
    CategoryResult,
    ReviewDecision,
    ReviewResult,
)

DIFF_MAX_CHARS = 80_000

BLOCK_ON_TO_CATEGORY: dict[str, str] = {
    "overengineering": "Overengineering",
    "poor_tests": "Tests",
    "duplication": "Duplication",
    "architectural_regression": "Architectural drift",
}


def run_review(
    diff: str,
    pr_meta: dict,
    block_on: list[str],
) -> ReviewResult:
    """Run LLM review on diff; apply block_on mapping and decision logic.

    Args:
        diff: Unified diff (full patch)
        pr_meta: {title, body, base_sha, head_sha, file_list}
        block_on: Config keys that can block (overengineering, poor_tests, etc.)

    Returns:
        ReviewResult with decision, categories, blocking_categories
    """
    diff_truncated = diff[:DIFF_MAX_CHARS] if len(diff) > DIFF_MAX_CHARS else diff
    if len(diff) > DIFF_MAX_CHARS:
        diff_truncated += "\n\n[... diff truncated ...]"

    pr_title = pr_meta.get("title", "")
    pr_body = pr_meta.get("body", "") or ""
    base_sha = pr_meta.get("base_sha", "") or ""
    head_sha = pr_meta.get("head_sha", "") or ""
    file_list = pr_meta.get("file_list", "") or ""

    out = _review_diff_impl(
        diff_truncated=diff_truncated,
        pr_title=pr_title,
        pr_body=pr_body,
        file_list=file_list,
        base_sha=base_sha,
        head_sha=head_sha,
    )

    categories = out.categories or []
    blocking_category_names = {
        BLOCK_ON_TO_CATEGORY.get(k, k)
        for k in (block_on or [])
        if k in BLOCK_ON_TO_CATEGORY
    }

    # Build category map by name
    by_name: dict[str, CategoryResult] = {}
    for c in categories:
        by_name[c.category] = c

    decision: ReviewDecision
    blocking_categories: list[str] = []

    # block_on empty → max decision is APPROVED_WITH_SUGGESTIONS (never BLOCKED)
    if blocking_category_names:
        for cat_name in blocking_category_names:
            c = by_name.get(cat_name)
            if c and c.grade == "FAIL":
                blocking_categories.append(cat_name)

        if blocking_categories:
            decision = "BLOCKED"
        else:
            decision = _compute_non_blocked_decision(categories)
    else:
        decision = _compute_non_blocked_decision(categories)

    return ReviewResult(
        decision=decision,
        categories=categories,
        blocking_categories=blocking_categories,
    )


def _compute_non_blocked_decision(categories: list[CategoryResult]) -> Literal["APPROVED", "APPROVED_WITH_SUGGESTIONS"]:
    """Any WARN or FAIL → APPROVED_WITH_SUGGESTIONS; else APPROVED."""
    for c in categories:
        if c.grade in ("WARN", "FAIL"):
            return "APPROVED_WITH_SUGGESTIONS"
    return "APPROVED"
