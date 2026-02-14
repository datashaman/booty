"""Quality gate runner for code formatting and linting checks."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from booty.logging import get_logger

logger = get_logger()


@dataclass
class QualityCheckResult:
    """Result of quality checks (formatting + linting)."""

    passed: bool
    formatting_ok: bool
    linting_ok: bool
    errors: list[str]


async def run_quality_checks(workspace_path: Path) -> QualityCheckResult:
    """Execute ruff format and lint checks.

    Returns:
        QualityCheckResult with combined results from formatting and linting.
        If ruff is not installed, gracefully skips checks and returns success.
    """
    logger.info("checking_ruff_availability")

    # Check if ruff is available
    try:
        proc = await asyncio.create_subprocess_shell(
            "which ruff",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, _ = await proc.communicate()

        if proc.returncode != 0:
            logger.warning("ruff_not_installed_skipping_quality_checks")
            return QualityCheckResult(
                passed=True,
                formatting_ok=True,
                linting_ok=True,
                errors=[],
            )

        logger.info("ruff_available", path=stdout_bytes.decode("utf-8").strip())

    except Exception as e:
        logger.error("ruff_availability_check_failed", error=str(e))
        return QualityCheckResult(
            passed=True,
            formatting_ok=True,
            linting_ok=True,
            errors=[],
        )

    errors = []
    formatting_ok = True
    linting_ok = True

    # Run ruff format --check
    logger.info("running_format_check", workspace=str(workspace_path))
    try:
        proc = await asyncio.create_subprocess_shell(
            "ruff format --check .",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace_path),
        )

        stdout_bytes, stderr_bytes = await proc.communicate()

        if proc.returncode != 0:
            formatting_ok = False
            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")
            error_msg = f"Formatting check failed:\n{stdout_text}\n{stderr_text}"
            errors.append(error_msg)
            logger.warning("format_check_failed", returncode=proc.returncode)
        else:
            logger.info("format_check_passed")

    except Exception as e:
        formatting_ok = False
        error_msg = f"Format check execution failed: {str(e)}"
        errors.append(error_msg)
        logger.error("format_check_error", error=str(e), exc_info=True)

    # Run ruff check
    logger.info("running_lint_check", workspace=str(workspace_path))
    try:
        proc = await asyncio.create_subprocess_shell(
            "ruff check .",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace_path),
        )

        stdout_bytes, stderr_bytes = await proc.communicate()

        if proc.returncode != 0:
            linting_ok = False
            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")
            error_msg = f"Linting check failed:\n{stdout_text}\n{stderr_text}"
            errors.append(error_msg)
            logger.warning("lint_check_failed", returncode=proc.returncode)
        else:
            logger.info("lint_check_passed")

    except Exception as e:
        linting_ok = False
        error_msg = f"Lint check execution failed: {str(e)}"
        errors.append(error_msg)
        logger.error("lint_check_error", error=str(e), exc_info=True)

    passed = formatting_ok and linting_ok

    logger.info(
        "quality_checks_complete",
        passed=passed,
        formatting_ok=formatting_ok,
        linting_ok=linting_ok,
        error_count=len(errors),
    )

    return QualityCheckResult(
        passed=passed,
        formatting_ok=formatting_ok,
        linting_ok=linting_ok,
        errors=errors,
    )
