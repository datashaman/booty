"""Tests for code_gen.validator."""
from pathlib import Path

import pytest

from booty.code_gen.validator import detect_prompt_leakage, validate_generated_code


def test_detect_prompt_leakage_returns_true_for_instructions():
    """Prompt leakage patterns are detected."""
    assert detect_prompt_leakage("## Test Generation Requirements\nfoo") is True
    assert detect_prompt_leakage("Generate unit tests alongside code changes") is True
    assert detect_prompt_leakage("CRITICAL: Return the FULL file content") is True
    assert detect_prompt_leakage("Place test files in the `test_files` array") is True
    assert detect_prompt_leakage("Use ONLY imports that exist in the project dependencies") is True
    assert detect_prompt_leakage("**Example Test Files (for reference):**") is True
    assert detect_prompt_leakage("Check /tmp/booty-123/tests/test_foo.py") is True


def test_detect_prompt_leakage_returns_false_for_clean_content():
    """Normal file content is not flagged."""
    assert detect_prompt_leakage("# Booty\n\nSelf-managing agent platform.") is False
    assert detect_prompt_leakage("def test_foo(): pass") is False
    assert detect_prompt_leakage("") is False


def test_validate_generated_code_raises_on_prompt_leakage():
    """Validation raises when content contains leaked prompt."""
    with pytest.raises(ValueError, match="prompt instructions instead of file content"):
        validate_generated_code(
            Path("README.md"),
            "# Booty\n\n## Test Generation Requirements\n\nGenerate unit tests...",
            Path("/tmp/workspace"),
        )


def test_validate_generated_code_passes_for_clean_markdown():
    """Validation passes for normal markdown content."""
    validate_generated_code(
        Path("README.md"),
        "# Booty\n\nSelf-managing agent platform.\n",
        Path("/tmp/workspace"),
    )


def test_validate_generated_code_passes_valid_python():
    """Validation passes for valid Python."""
    validate_generated_code(
        Path("foo.py"),
        "def bar() -> int:\n    return 42\n",
        Path("/tmp/workspace"),
    )


def test_validate_generated_code_raises_on_syntax_error():
    """Validation raises for invalid Python syntax."""
    with pytest.raises(ValueError, match="syntax error"):
        validate_generated_code(
            Path("foo.py"),
            "def bar(:\n    return\n",
            Path("/tmp/workspace"),
        )
