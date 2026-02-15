"""Test generation module for language-agnostic test creation.

This module provides:
- Convention detection: Infers test framework, directory structure, and naming patterns
- Import validation: Prevents hallucinated package imports in generated tests

Public API:
- detect_conventions: Analyze repository to infer test conventions
- validate_test_imports: Validate generated test imports against project dependencies
- DetectedConventions: Model for detected test conventions
"""

from booty.test_generation.detector import detect_conventions
from booty.test_generation.models import DetectedConventions
from booty.test_generation.validator import validate_test_imports

__all__ = [
    "detect_conventions",
    "validate_test_imports",
    "DetectedConventions",
]
