"""Test-driven refinement loop for code generation."""

from pathlib import Path

from booty.code_gen.validator import validate_generated_code
from booty.llm.models import FileChange
from booty.llm.prompts import regenerate_code_changes
from booty.logging import get_logger
from booty.test_runner.config import BootyConfig
from booty.test_runner.executor import execute_tests
from booty.test_runner.parser import extract_error_summary, extract_files_from_output

logger = get_logger()


async def refine_until_tests_pass(
    workspace_path: Path,
    config: BootyConfig,
    current_changes: list[FileChange],
    task_description: str,
    issue_title: str,
    issue_body: str,
    test_conventions: str = "",
) -> tuple[bool, list[FileChange], str | None]:
    """Run test-refine iteration loop until tests pass or max retries exhausted.

    Each iteration:
    1. Execute tests
    2. If pass: return success
    3. If fail on last attempt: return failure with error
    4. Otherwise: extract error, regenerate affected files, retry

    Args:
        workspace_path: Absolute path to workspace root
        config: Booty configuration with test settings
        current_changes: Current list of file changes applied
        task_description: Summary of what needs to be done
        issue_title: Issue title text
        issue_body: Issue body/description text
        test_conventions: Formatted test conventions string (empty if none detected)

    Returns:
        Tuple of (tests_passed, final_changes, error_message_or_none)
        - tests_passed: True if tests passed, False otherwise
        - final_changes: Final list of FileChange objects after all iterations
        - error_message: Error summary if tests failed, None if passed
    """
    logger.info(
        "refinement_loop_started",
        max_retries=config.max_retries,
        test_command=config.test_command,
    )

    for attempt in range(1, config.max_retries + 1):
        logger.info("refinement_attempt", attempt=attempt, max_retries=config.max_retries)

        # Execute tests
        result = await execute_tests(config.test_command, config.timeout, workspace_path)

        # Check if tests passed
        if result.exit_code == 0:
            logger.info(
                "tests_passed",
                attempt=attempt,
                exit_code=result.exit_code,
            )
            return (True, current_changes, None)

        # Tests failed - extract error summary
        error_summary = extract_error_summary(result.stderr, result.stdout)
        logger.warning(
            "tests_failed",
            attempt=attempt,
            exit_code=result.exit_code,
            timed_out=result.timed_out,
            error_lines=len(error_summary.split("\n")),
        )

        # If this was the last attempt, return failure
        if attempt == config.max_retries:
            final_error = (
                f"After {attempt}/{config.max_retries} attempt(s), tests still failing.\n\n"
                f"Latest error:\n{error_summary}"
            )
            logger.error("refinement_exhausted", attempts=attempt, max_retries=config.max_retries)
            return (False, current_changes, final_error)

        # Not the last attempt - regenerate code
        logger.info("regenerating_code", attempt=attempt)

        # Extract failing files from test output
        failed_files = extract_files_from_output(
            result.stderr + "\n" + result.stdout,
            workspace_path,
        )

        # If no files identified from traceback, use all originally modified files as fallback
        if not failed_files:
            failed_files = {change.path for change in current_changes}
            logger.warning(
                "no_files_in_traceback_using_all",
                fallback_count=len(failed_files),
            )

        logger.info("files_to_regenerate", files=list(failed_files), count=len(failed_files))

        # Build current file contents by reading from workspace
        file_contents = {}
        for file_path in failed_files:
            full_path = workspace_path / file_path
            if full_path.exists():
                file_contents[file_path] = full_path.read_text()
            else:
                # File doesn't exist yet (might be a new file that failed)
                # Find it in current_changes
                for change in current_changes:
                    if change.path == file_path:
                        file_contents[file_path] = change.content
                        break

        # Call LLM to regenerate code
        logger.info("calling_llm_for_regeneration", file_count=len(file_contents))
        regenerated_plan = regenerate_code_changes(
            task_description,
            file_contents,
            error_summary,
            ", ".join(sorted(failed_files)),
            issue_title,
            issue_body,
            test_conventions=test_conventions,
        )

        logger.info(
            "code_regenerated",
            changes_count=len(regenerated_plan.changes),
            approach=regenerated_plan.approach,
        )

        # Validate regenerated code
        logger.info("validating_regenerated_code", count=len(regenerated_plan.changes))
        for change in regenerated_plan.changes:
            if change.operation == "delete":
                continue  # Skip validation for deletions

            validate_generated_code(
                Path(change.path),
                change.content,
                workspace_path,
            )
            logger.debug(
                "regenerated_code_validated",
                path=change.path,
                operation=change.operation,
            )

        # Apply regenerated changes to workspace
        logger.info("applying_regenerated_changes", count=len(regenerated_plan.changes))
        for change in regenerated_plan.changes:
            full_path = workspace_path / change.path

            if change.operation in ("create", "modify"):
                # Create parent directories if needed
                full_path.parent.mkdir(parents=True, exist_ok=True)
                # Write content
                full_path.write_text(change.content)
                logger.debug(
                    "regenerated_file_written",
                    path=change.path,
                    operation=change.operation,
                    size=len(change.content),
                )
            elif change.operation == "delete":
                # Remove file if it exists
                if full_path.exists():
                    full_path.unlink()
                    logger.debug("regenerated_file_deleted", path=change.path)

        # Update current_changes to reflect regenerated code
        # Replace old changes with new ones for regenerated files
        regenerated_paths = {change.path for change in regenerated_plan.changes}
        updated_changes = []

        # Keep non-regenerated files
        for change in current_changes:
            if change.path not in regenerated_paths:
                updated_changes.append(change)

        # Add regenerated files
        updated_changes.extend(regenerated_plan.changes)

        current_changes = updated_changes
        logger.info(
            "refinement_iteration_complete",
            attempt=attempt,
            total_changes=len(current_changes),
        )

    # Should never reach here (loop should return from inside)
    return (False, current_changes, "Unknown error - refinement loop ended unexpectedly")
