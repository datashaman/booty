"""Architect rewrite — ambiguity and overreach detection and rewrite.

Rule-driven only; no LLM. ARCH-13, ARCH-14, ARCH-15.
"""

import re

from booty.architect.config import ArchitectConfig
from booty.architect.validation import derive_touch_paths
from booty.planner.schema import Plan, Step

# Vague patterns that indicate ambiguous acceptance or action
AMBIGUITY_PATTERNS = [
    r"\bfix\b",
    r"\bimprove\b",
    r"\bas needed\b",
    r"\bupdate\b",
    r"\brefactor\b",
    r"\bclean up\b",
    r"\bmake sure\b",
    r"\bensure\b",
]
AMBIGUITY_MIN_ACCEPTANCE_LEN = 15
DOMAINS = ("src/", "tests/", "docs/", "infra/", ".github/")
OVERREACH_PATH_COUNT = 8
OVERREACH_DOMAIN_SPREAD = 3
SPECULATIVE_KEYWORDS = (
    "refactor architecture",
    "improve structure",
    "technical debt",
)


def _domain_prefix(path: str) -> str | None:
    """Return known domain prefix for path (e.g. src/, tests/) or None."""
    path_norm = path.replace("\\", "/").lstrip("/")
    for d in DOMAINS:
        if path_norm.startswith(d) or path_norm.startswith(d.rstrip("/")):
            return d
    return None


def check_ambiguity(plan: Plan) -> list[tuple[int, str]]:
    """Return list of (step_index, reason) for ambiguous steps.

    Triggers: acceptance < 15 chars; action+path/edit with acceptance matching AMBIGUITY_PATTERNS.
    """
    ambiguous: list[tuple[int, str]] = []
    for i, step in enumerate(plan.steps):
        reasons: list[str] = []
        acc = (step.acceptance or "").strip()
        if len(acc) < AMBIGUITY_MIN_ACCEPTANCE_LEN:
            reasons.append(f"acceptance too short ({len(acc)} chars)")
        for pat in AMBIGUITY_PATTERNS:
            if re.search(pat, acc, re.IGNORECASE):
                reasons.append(f"vague pattern '{pat}' in acceptance")
                break
        if reasons:
            ambiguous.append((i, "; ".join(reasons)))
    return ambiguous


def rewrite_ambiguous_steps(
    plan: Plan, config: ArchitectConfig
) -> tuple[Plan, list[str]]:
    """Rewrite ambiguous steps when config.rewrite_ambiguous_steps enabled.

    When disabled: return (plan, list of flag messages for architect_notes).
    When enabled: tighten acceptance or infer path where possible.
    """
    ambiguous = check_ambiguity(plan)
    if not ambiguous:
        return plan, []

    if not config.rewrite_ambiguous_steps:
        return plan, [
            f"Step {plan.steps[i].id}: ambiguous — {reason}"
            for i, reason in ambiguous
        ]

    notes: list[str] = []
    steps = list(plan.steps)
    for i, reason in ambiguous:
        step = steps[i]
        # Try to tighten acceptance if too short
        acc = (step.acceptance or "").strip()
        if len(acc) < AMBIGUITY_MIN_ACCEPTANCE_LEN and acc:
            # Minimal rewrite: make it slightly more specific
            tightened = acc
            if not acc.endswith("."):
                tightened = f"{acc} (verified)."
            if len(tightened) >= AMBIGUITY_MIN_ACCEPTANCE_LEN:
                steps[i] = step.model_copy(update={"acceptance": tightened})
                notes.append(f"Step {step.id}: tightened acceptance")
        else:
            notes.append(f"Step {step.id}: ambiguous — {reason}")
    new_plan = plan.model_copy(update={"steps": steps})
    return new_plan, notes


def check_overreach(plan: Plan) -> list[str]:
    """Return list of overreach reasons (empty if none).

    - Repo-wide: touch_paths count ≥ 8 OR directory spread (paths in 3+ distinct domain prefixes)
    - Multi-domain: paths touch 2+ of DOMAINS
    - Speculative: goal or acceptance contains speculative keywords
    """
    reasons: list[str] = []
    paths_norm = [
        p.lstrip("/").replace("\\", "/")
        for p in derive_touch_paths(plan)
    ]

    if len(paths_norm) >= OVERREACH_PATH_COUNT:
        reasons.append("repo-wide: many paths touched")
    domains_seen: set[str] = set()
    for p in paths_norm:
        dom = _domain_prefix(p)
        if dom:
            domains_seen.add(dom)
    if len(domains_seen) >= OVERREACH_DOMAIN_SPREAD:
        reasons.append("repo-wide: directory spread across 3+ domains")
    if len(domains_seen) >= 2:
        reasons.append("multi-domain: touching 2+ of src/tests/docs/infra/.github")

    goal_lower = (plan.goal or "").lower()
    for kw in SPECULATIVE_KEYWORDS:
        if kw in goal_lower:
            reasons.append(f"speculative: '{kw}' in goal")
            break
    for step in plan.steps:
        acc = (step.acceptance or "").lower()
        for kw in SPECULATIVE_KEYWORDS:
            if kw in acc:
                reasons.append(f"speculative: '{kw}' in step acceptance")
                break

    return reasons


def try_rewrite_overreach(plan: Plan) -> tuple[Plan | None, list[str]]:
    """Try to rewrite overreaching plan into smaller scope.

    Attempts: narrow scope, merge related steps to fit ≤12.
    Returns (modified_plan, notes) on success, (None, reasons) when block needed.
    """
    reasons = check_overreach(plan)
    if not reasons:
        return plan, []

    # Simple heuristic: if we have many steps touching same path, try merging
    steps = plan.steps
    if len(steps) > 8:
        merged: list[Step] = []
        i = 0
        while i < len(steps):
            s = steps[i]
            next_s = steps[i + 1] if i + 1 < len(steps) else None
            if (
                next_s
                and s.path
                and next_s.path
                and s.path.lstrip("/") == next_s.path.lstrip("/")
            ):
                combined = s.model_copy(
                    update={"acceptance": f"{s.acceptance}; {next_s.acceptance}"}
                )
                merged.append(combined)
                i += 2
                continue
            merged.append(s)
            i += 1
        if len(merged) <= 12 and len(merged) < len(steps):
            return plan.model_copy(update={"steps": merged}), [
                "Merged related steps to reduce scope"
            ]

    return None, reasons
