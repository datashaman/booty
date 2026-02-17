"""Architect validation — structural integrity, path consistency, risk recomputation.

Rule-driven only; no LLM. ARCH-06 through ARCH-12.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError

from booty.planner.schema import Plan, Step

VALID_ACTIONS = frozenset({"read", "add", "edit", "run", "verify", "research"})
PATH_ACTIONS = frozenset({"read", "edit", "add", "research"})  # require path
NO_PATH_ACTIONS = frozenset({"run", "verify"})  # path optional/ignored

# Risk classification paths (HIGH severity)
HIGH_RISK_PATTERNS = (
    ".github/workflows/",
    "infra/",
    "migrations",
    "package-lock.json",
    "yarn.lock",
    "uv.lock",
    "poetry.lock",
    "Cargo.lock",
)
MEDIUM_RISK_FILES = (
    "pyproject.toml",
    "package.json",
    "requirements.txt",
    "Cargo.toml",
)


@dataclass
class ValidationResult:
    """Result of validation (passed, errors, flags for architect_notes, whether to block)."""

    passed: bool
    errors: list[str]
    blocks: bool
    flags: list[str] | None = None  # Non-blocking notes for architect_notes


def _normalize_plan(plan: Plan | dict) -> Plan | None:
    """Normalize plan to Plan. Returns None on ValidationError."""
    if isinstance(plan, Plan):
        return plan
    try:
        return Plan.model_validate(plan)
    except ValidationError:
        return None


def validate_structural(plan: Plan | dict) -> ValidationResult:
    """Validate structural integrity (ARCH-06, ARCH-07, ARCH-08).

    - steps length ≤ 12
    - each step has id and action
    - each action ∈ VALID_ACTIONS
    """
    # Pre-check dict to surface specific errors before Pydantic (e.g. >12 steps, invalid action)
    if isinstance(plan, dict):
        steps_raw = plan.get("steps", [])
        if len(steps_raw) > 12:
            return ValidationResult(
                passed=False,
                errors=["Steps > 12"],
                blocks=True,
                flags=None,
            )
        for i, s in enumerate(steps_raw):
            if isinstance(s, dict):
                aid = s.get("id", f"P{i+1}")
                action = s.get("action")
            else:
                aid = getattr(s, "id", f"P{i+1}")
                action = getattr(s, "action", None)
            if action is not None and action not in VALID_ACTIONS:
                return ValidationResult(
                    passed=False,
                    errors=[f"Step {aid}: invalid action {action!r}"],
                    blocks=True,
                    flags=None,
                )
    p = _normalize_plan(plan)
    if p is None:
        return ValidationResult(
            passed=False,
            errors=["Invalid plan structure (parse or schema error)"],
            blocks=True,
            flags=None,
        )
    errors: list[str] = []
    if len(p.steps) > 12:
        errors.append("Steps > 12")
        return ValidationResult(passed=False, errors=errors, blocks=True, flags=None)
    for i, step in enumerate(p.steps):
        if not (step.id and step.action):
            errors.append(f"Step {i}: missing id or action")
        elif step.action not in VALID_ACTIONS:
            errors.append(f"Step {step.id}: invalid action {step.action!r}")
    if errors:
        return ValidationResult(passed=False, errors=errors, blocks=True, flags=None)
    return ValidationResult(passed=True, errors=[], blocks=False, flags=None)


def derive_touch_paths(plan: Plan) -> list[str]:
    """Union of step.path for read/edit/add/research steps with non-empty path.

    Mirrors planner/generation.py but includes research (ARCH-08).
    """
    paths: set[str] = set()
    for s in plan.steps:
        if s.action in PATH_ACTIONS and s.path:
            p = s.path.lstrip("/").strip()
            if p:
                paths.add(p)
    return sorted(paths)


def validate_paths(plan: Plan | dict) -> ValidationResult:
    """Validate path consistency and empty path rules (ARCH-09, ARCH-10).

    - touch_paths mismatch: flag only (don't block)
    - read/add/edit/research with no path: BLOCK
    - run/verify with or without path: valid (path ignored)
    - All run/verify (touch_paths empty): flag in architect_notes, approve
    """
    p = _normalize_plan(plan)
    if p is None:
        return ValidationResult(
            passed=False,
            errors=["Invalid plan structure"],
            blocks=True,
            flags=None,
        )
    errors: list[str] = []
    flags: list[str] = []
    # touch_paths mismatch: flag only
    expected = set(derive_touch_paths(p))
    actual = set(p.touch_paths) if p.touch_paths else set()
    if expected != actual:
        flags.append(
            f"touch_paths mismatch: expected {sorted(expected)}, got {sorted(actual)}"
        )
    if not expected and not actual:
        flags.append("All steps are run/verify; no file paths touched")
    # Empty path rules: PATH_ACTIONS require path
    for i, step in enumerate(p.steps):
        if step.action in PATH_ACTIONS:
            path_val = step.path if step.path else ""
            if not path_val.strip():
                errors.append(
                    f"Step {step.id} ({step.action}): path required for read/add/edit/research"
                )
    if errors:
        return ValidationResult(passed=False, errors=errors, blocks=True, flags=flags or None)
    return ValidationResult(
        passed=True, errors=[], blocks=False, flags=flags if flags else None
    )


def compute_risk_from_touch_paths(
    touch_paths: list[str],
) -> Literal["LOW", "MEDIUM", "HIGH"]:
    """Compute risk from touch_paths (ARCH-11).

    HIGH: workflows, infra, migrations, lockfiles
    MEDIUM: pyproject.toml, package.json, requirements.txt, Cargo.toml
    LOW: else
    """
    risk = "LOW"
    for path in touch_paths:
        path_lower = path.lower()
        # HIGH
        for pat in HIGH_RISK_PATTERNS:
            if pat in path_lower or path_lower.endswith(pat):
                return "HIGH"
        # MEDIUM
        path_parts = path_lower.replace("\\", "/").split("/")
        if any(p in MEDIUM_RISK_FILES for p in path_parts):
            risk = "MEDIUM"
    return risk  # type: ignore[return-value]


def ensure_touch_paths_and_risk(plan: Plan) -> Plan:
    """Recompute touch_paths and risk; override risk if different (ARCH-12)."""
    touch_paths = derive_touch_paths(plan)
    risk = compute_risk_from_touch_paths(touch_paths)
    return plan.model_copy(
        update={
            "touch_paths": touch_paths,
            "risk_level": risk,
        }
    )
