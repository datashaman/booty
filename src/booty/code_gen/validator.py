"""Pre-commit validation for LLM-generated Python code.

This module provides syntax and import validation to prevent broken code
from being committed. Only validates Python files (.py), skipping other
file types silently.
"""

import ast
from pathlib import Path

# Substrings that indicate prompt/instructions leaked into file content
_PROMPT_LEAKAGE_PATTERNS = (
    "## Test Generation Requirements",
    "Generate unit tests alongside code changes",
    "CRITICAL: Return the FULL file content",
    "Place test files in the `test_files` array",
    "Use ONLY imports that exist in the project dependencies",
    "**Example Test Files (for reference):**",
    "/tmp/booty-",
)


def detect_prompt_leakage(content: str) -> bool:
    """Detect if LLM output contains prompt instructions instead of file content.

    Returns True if content appears to include leaked prompt text.
    """
    return any(pattern in content for pattern in _PROMPT_LEAKAGE_PATTERNS)


def validate_python_syntax(filepath: Path, content: str) -> tuple[bool, str | None]:
    """Validate Python file syntax without executing.

    Uses ast.parse() to check if content is syntactically valid Python code.

    Args:
        filepath: Path to the file (used in error messages)
        content: Python source code to validate

    Returns:
        Tuple of (valid: bool, error_message: str | None)
        - (True, None) if syntax is valid
        - (False, error_message) if syntax error found, with line number and details
    """
    try:
        ast.parse(content, filename=str(filepath))
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"


def validate_generated_code(filepath: Path, content: str, workspace_root: Path) -> None:
    """Validate code before committing - fail fast on errors.

    Validates all files for prompt leakage; only .py files get syntax validation.

    Args:
        filepath: Path to the file being validated
        content: File content to validate
        workspace_root: Root directory of the workspace (unused for now, reserved for future import checks)

    Raises:
        ValueError: If validation fails (prompt leakage or syntax error in Python file)
    """
    # Prompt leakage: reject content that contains our instructions
    if detect_prompt_leakage(content):
        raise ValueError(
            "Generated content appears to include prompt instructions instead of file content; "
            "regenerating."
        )

    # Only validate Python files for syntax
    if not str(filepath).endswith('.py'):
        return  # Skip syntax check for non-Python files

    # Syntax validation
    valid_syntax, syntax_error = validate_python_syntax(filepath, content)
    if not valid_syntax:
        raise ValueError(f"Generated code has syntax error: {syntax_error}")

    # Note: Import validation is intentionally not implemented per RESEARCH.md open question #2
    # Third-party imports would require full dependency resolution (installing deps in workspace)
    # CI will catch import errors instead
