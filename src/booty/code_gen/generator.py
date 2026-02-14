"""Main orchestrator for issue-to-PR pipeline."""

import os
from pathlib import Path

from booty.code_gen.refiner import refine_until_tests_pass
from booty.code_gen.security import PathRestrictor
from booty.code_gen.validator import validate_generated_code
from booty.config import Settings
from booty.git.operations import commit_changes, format_commit_message, push_to_remote
from booty.github.pulls import (
    add_self_modification_metadata,
    create_pull_request,
    format_pr_body,
    format_self_modification_pr_body,
)
from booty.jobs import Job
from booty.llm.prompts import analyze_issue, generate_code_changes
from booty.llm.token_budget import TokenBudget
from booty.logging import get_logger
from booty.repositories import Workspace
from booty.self_modification.safety import validate_changes_against_protected_paths
from booty.test_runner.config import load_booty_config
from booty.test_runner.quality import run_quality_checks

logger = get_logger()


async def process_issue_to_pr(
    job: Job, workspace: Workspace, settings: Settings, is_self_modification: bool = False
) -> tuple[int, bool, str | None]:
    """Process issue from analysis to PR creation.

    Pipeline:
    1. List repo files
    2. Analyze issue to get structured understanding
    3. Check file count limit
    4. Validate path security
    4b. For self-modification: validate against protected paths
    5. Load existing file contents
    6. Check token budget
    7. Generate code changes
    8. Validate generated code
    9. Apply changes to workspace
    10. Run test-driven refinement loop
    10b. For self-modification: run quality checks (ruff)
    11. Commit changes
    12. Push to remote
    13. Create pull request (draft if tests failed OR always draft for self-modification)

    Args:
        job: Job containing issue details
        workspace: Workspace with repository clone
        settings: Application settings
        is_self_modification: Whether this is a self-modification job (default False)

    Returns:
        Tuple of (pr_number, tests_passed, error_message)
        - pr_number: GitHub PR number
        - tests_passed: True if tests passed after refinement
        - error_message: Error details if tests failed, None if passed

    Raises:
        ValueError: If issue exceeds limits, validation fails, or .booty.yml missing
    """
    try:
        logger.info("process_issue_to_pr_started", job_id=job.job_id, issue_number=job.issue_number)

        # Step 1: List repo files
        logger.info("listing_repo_files", workspace_path=workspace.path)
        repo_files = []
        workspace_path = Path(workspace.path)
        for root, dirs, files in os.walk(workspace_path):
            # Exclude .git directory
            if ".git" in dirs:
                dirs.remove(".git")

            # Add files relative to workspace root
            for file in files:
                full_path = Path(root) / file
                relative_path = full_path.relative_to(workspace_path)
                repo_files.append(str(relative_path))

        repo_files.sort()  # Deterministic ordering
        logger.info("repo_files_listed", count=len(repo_files))

        # Step 2: Analyze issue
        logger.info("analyzing_issue", issue_number=job.issue_number)
        issue_title = job.payload["issue"]["title"]
        issue_body = job.payload["issue"]["body"] or ""
        repo_file_list = "\n".join(repo_files)

        analysis = analyze_issue(issue_title, issue_body, repo_file_list)
        logger.info(
            "issue_analyzed",
            files_to_modify=len(analysis.files_to_modify),
            files_to_create=len(analysis.files_to_create),
            files_to_delete=len(analysis.files_to_delete),
            commit_type=analysis.commit_type,
            commit_scope=analysis.commit_scope,
            summary=analysis.summary,
        )

        # Step 3: Check file count
        total_file_changes = (
            len(analysis.files_to_modify)
            + len(analysis.files_to_create)
            + len(analysis.files_to_delete)
        )
        if total_file_changes > settings.MAX_FILES_PER_ISSUE:
            raise ValueError(
                f"Issue requires too many file changes: {total_file_changes} > {settings.MAX_FILES_PER_ISSUE}"
            )
        logger.info("file_count_check_passed", total_changes=total_file_changes)

        # Step 4: Path security check
        logger.info("validating_path_security")
        restrictor = PathRestrictor.from_config(
            Path(workspace.path), settings.RESTRICTED_PATHS
        )
        all_paths = (
            analysis.files_to_modify
            + analysis.files_to_create
            + analysis.files_to_delete
        )
        restrictor.validate_all_paths(all_paths)
        logger.info("path_security_validated", paths_checked=len(all_paths))

        # Step 4b: Self-modification protected path validation
        if is_self_modification:
            logger.info("validating_self_modification_protected_paths", paths_count=len(all_paths))
            changes_dicts = [{"path": p} for p in all_paths]
            is_valid, reason = validate_changes_against_protected_paths(
                changes_dicts, workspace_path
            )
            if not is_valid:
                raise ValueError(f"Self-modification blocked: {reason}")
            logger.info("protected_paths_validated")

        # Step 5: Load existing file contents
        logger.info("loading_existing_files", count=len(analysis.files_to_modify))
        file_contents = {}
        for file_path in analysis.files_to_modify:
            full_path = workspace_path / file_path
            if full_path.exists():
                file_contents[file_path] = full_path.read_text()
                logger.debug("file_loaded", path=file_path, size=len(file_contents[file_path]))
            else:
                logger.warning("file_not_found_skipping", path=file_path)

        # Step 6: Token budget check
        logger.info("checking_token_budget")
        budget = TokenBudget(settings.LLM_MAX_CONTEXT_TOKENS)

        # Build base content for budget check
        base_content = f"Task: {analysis.task_description}\n\nIssue: {issue_title}\n{issue_body}"

        # Check if we need to trim files
        result = budget.check_budget(
            "You are a code generation assistant.",
            base_content + "\n\n" + "\n".join([f"{k}: {v}" for k, v in file_contents.items()]),
        )

        if not result["fits"]:
            logger.warning(
                "context_overflow_detected",
                overflow_by=result["overflow_by"],
                attempting_file_selection=True,
            )
            # Try to select files within budget
            file_contents = budget.select_files_within_budget(
                "You are a code generation assistant.",
                base_content,
                file_contents,
                settings.LLM_MAX_CONTEXT_TOKENS - budget.max_output_tokens,
            )

            # Check if even base content fits
            if len(file_contents) == 0:
                raise ValueError("Context too large: even base content doesn't fit within budget")

            logger.info("files_selected_within_budget", selected_count=len(file_contents))
        else:
            logger.info("token_budget_check_passed", remaining=result["remaining"])

        # Step 7: Generate code
        logger.info("generating_code_changes")
        plan = generate_code_changes(
            analysis.task_description,
            file_contents,
            issue_title,
            issue_body,
        )
        logger.info(
            "code_generated",
            changes_count=len(plan.changes),
            approach=plan.approach,
        )

        # Step 8: Validate generated code
        logger.info("validating_generated_code", count=len(plan.changes))
        for change in plan.changes:
            if change.operation == "delete":
                continue  # Skip validation for deletions

            validate_generated_code(
                Path(change.path),
                change.content,
                Path(workspace.path),
            )
            logger.debug("code_validated", path=change.path, operation=change.operation)
        logger.info("code_validation_complete")

        # Step 9: Apply changes to workspace
        logger.info("applying_changes_to_workspace", count=len(plan.changes))
        modified_paths = []
        deleted_paths = []

        for change in plan.changes:
            full_path = workspace_path / change.path

            if change.operation in ("create", "modify"):
                # Create parent directories if needed
                full_path.parent.mkdir(parents=True, exist_ok=True)
                # Write content
                full_path.write_text(change.content)
                modified_paths.append(change.path)
                logger.debug(
                    "file_written",
                    path=change.path,
                    operation=change.operation,
                    size=len(change.content),
                )
            elif change.operation == "delete":
                # Remove file if it exists
                if full_path.exists():
                    full_path.unlink()
                    deleted_paths.append(change.path)
                    logger.debug("file_deleted", path=change.path)

        logger.info(
            "changes_applied",
            modified=len(modified_paths),
            deleted=len(deleted_paths),
        )

        # Step 10: Test-driven refinement
        logger.info("loading_test_configuration")
        try:
            config = load_booty_config(workspace_path)
        except FileNotFoundError as e:
            raise ValueError(
                "Missing .booty.yml configuration. "
                "Test-driven refinement requires a .booty.yml file in the repository root. "
                f"Details: {str(e)}"
            ) from e

        logger.info(
            "test_config_loaded",
            test_command=config.test_command,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

        logger.info("starting_refinement_loop")
        tests_passed, final_changes, error_message = await refine_until_tests_pass(
            workspace_path,
            config,
            plan.changes,
            analysis.task_description,
            issue_title,
            issue_body,
        )

        # Step 10b: Self-modification quality checks
        if is_self_modification:
            logger.info("running_self_modification_quality_checks")
            quality_result = await run_quality_checks(workspace_path)
            logger.info(
                "quality_checks_complete",
                passed=quality_result.passed,
                formatting_ok=quality_result.formatting_ok,
                linting_ok=quality_result.linting_ok,
            )
            if not quality_result.passed:
                # Append quality errors to error_message
                quality_errors = "\n".join(quality_result.errors)
                if error_message:
                    error_message = f"{error_message}\n\nQuality Check Failures:\n{quality_errors}"
                else:
                    error_message = f"Quality Check Failures:\n{quality_errors}"
                tests_passed = False
                logger.warning("quality_checks_failed", errors_count=len(quality_result.errors))

        # If changes were regenerated (final_changes differ from plan.changes), re-apply them
        if final_changes != plan.changes:
            logger.info("reapplying_regenerated_changes", count=len(final_changes))
            modified_paths = []
            deleted_paths = []

            for change in final_changes:
                full_path = workspace_path / change.path

                if change.operation in ("create", "modify"):
                    # Create parent directories if needed
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    # Write content
                    full_path.write_text(change.content)
                    modified_paths.append(change.path)
                    logger.debug(
                        "final_file_written",
                        path=change.path,
                        operation=change.operation,
                        size=len(change.content),
                    )
                elif change.operation == "delete":
                    # Remove file if it exists
                    if full_path.exists():
                        full_path.unlink()
                        deleted_paths.append(change.path)
                        logger.debug("final_file_deleted", path=change.path)

            logger.info(
                "final_changes_applied",
                modified=len(modified_paths),
                deleted=len(deleted_paths),
            )

        # Step 11: Commit
        logger.info("committing_changes")
        commit_message = format_commit_message(
            analysis.commit_type,
            analysis.commit_scope,
            analysis.summary,
            plan.approach,
            job.issue_number,
        )
        commit_sha = commit_changes(
            workspace.repo,
            modified_paths,
            commit_message,
            deleted_paths if deleted_paths else None,
        )
        logger.info("changes_committed", sha=commit_sha)

        # Step 12: Push
        logger.info("pushing_to_remote", branch=workspace.branch)
        await push_to_remote(workspace.repo, settings.GITHUB_TOKEN)
        logger.info("push_complete")

        # Step 13: Create PR
        # Self-modification PRs are ALWAYS draft, regardless of test results
        is_draft = (not tests_passed) if not is_self_modification else True
        logger.info("creating_pull_request", draft=is_draft, is_self_modification=is_self_modification)

        # Format PR title
        if analysis.commit_scope:
            pr_title = f"{analysis.commit_type}({analysis.commit_scope}): {analysis.summary}"
        else:
            pr_title = f"{analysis.commit_type}: {analysis.summary}"

        # Convert FileChange models to dicts for PR body (use final_changes)
        changes_dicts = [
            {
                "path": change.path,
                "operation": change.operation,
                "explanation": change.explanation,
            }
            for change in final_changes
        ]

        # Format PR body based on self-modification status
        if is_self_modification:
            # Load protected paths from config
            protected_paths = config.protected_paths if config.protected_paths else []
            changed_files = [change.path for change in final_changes]
            pr_body = format_self_modification_pr_body(
                plan.approach,
                changes_dicts,
                plan.testing_notes,
                job.issue_number,
                protected_paths,
                changed_files,
            )
        else:
            pr_body = format_pr_body(
                plan.approach,
                changes_dicts,
                plan.testing_notes,
                job.issue_number,
            )

        # If tests failed, append error context to PR body
        if not tests_passed:
            pr_body += f"\n\n## Test Failures\n\nTests did not pass after refinement attempts.\n\n```\n{error_message}\n```\n"

        pr_number = create_pull_request(
            settings.GITHUB_TOKEN,
            settings.TARGET_REPO_URL,
            workspace.branch,
            settings.TARGET_BRANCH,
            pr_title,
            pr_body,
            draft=is_draft,
        )

        # Add self-modification metadata if needed
        if is_self_modification:
            logger.info("adding_self_modification_metadata", pr_number=pr_number)
            add_self_modification_metadata(
                settings.GITHUB_TOKEN,
                settings.TARGET_REPO_URL,
                pr_number,
                settings.BOOTY_SELF_MODIFY_REVIEWER,
            )
            logger.info("self_modification_metadata_added")

        logger.info(
            "process_issue_to_pr_complete",
            pr_number=pr_number,
            tests_passed=tests_passed,
            job_id=job.job_id,
            issue_number=job.issue_number,
        )

        return (pr_number, tests_passed, error_message)

    except Exception as e:
        logger.error(
            "process_issue_to_pr_failed",
            job_id=job.job_id,
            issue_number=job.issue_number,
            error=str(e),
            exc_info=True,
        )
        raise
