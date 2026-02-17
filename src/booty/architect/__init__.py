"""Architect agent — validates and refines plans before Builder execution."""

from booty.architect.validation import (
    ValidationResult,
    compute_risk_from_touch_paths,
    derive_touch_paths,
    ensure_touch_paths_and_risk,
    validate_paths,
    validate_structural,
)

__all__ = [
    "ValidationResult",
    "compute_risk_from_touch_paths",
    "derive_touch_paths",
    "ensure_touch_paths_and_risk",
    "validate_paths",
    "validate_structural",
]
