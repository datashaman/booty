"""Test execution with subprocess and timeout handling."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from booty.logging import get_logger

logger = get_logger()


@dataclass
class TestResult:
    """Result of test execution."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


async def execute_tests(
    command: str,
    timeout: int,
    workspace_path: Path,
) -> TestResult:
    """Execute test command with timeout.

    Args:
        command: Shell command to execute
        timeout: Timeout in seconds
        workspace_path: Working directory for command execution

    Returns:
        TestResult with exit code and output

    Note:
        Never raises - captures all failures in TestResult
    """
    logger.info("executing_tests", command=command, timeout=timeout)

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace_path),
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            logger.info(
                "test_execution_complete",
                exit_code=proc.returncode,
                stdout_len=len(stdout_bytes),
                stderr_len=len(stderr_bytes),
            )

            return TestResult(
                exit_code=proc.returncode if proc.returncode is not None else -1,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                timed_out=False,
            )

        except asyncio.TimeoutError:
            logger.warning("test_timeout_killing_process", timeout=timeout)
            proc.kill()
            await proc.wait()  # Prevent zombie

            return TestResult(
                exit_code=-1,
                stdout="",
                stderr=f"Test execution exceeded timeout of {timeout} seconds",
                timed_out=True,
            )

    except Exception as e:
        logger.error("test_execution_error", error=str(e), exc_info=True)
        return TestResult(
            exit_code=-1,
            stdout="",
            stderr=f"Test execution failed: {str(e)}",
            timed_out=False,
        )
