"""Verifier job runner — clone, test, update check run."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from github import UnknownObjectException
from pydantic import ValidationError

from booty.config import Settings, verifier_enabled
from booty.github.checks import create_check_run, edit_check_run, get_verifier_repo
from booty.github.comments import post_verifier_failure_comment
from booty.github.promotion import promote_to_ready_for_review
from booty.jobs import Job
from booty.logging import get_logger
from booty.test_runner.config import (
    BootyConfig,
    BootyConfigV1,
    load_booty_config,
    load_booty_config_from_content,
)
from booty.test_runner.executor import execute_tests

from booty.verifier.imports import (
    compile_sweep,
    parse_setup_stderr,
    prepare_check_annotations,
    validate_imports,
)
from booty.verifier.job import VerifierJob
from booty.verifier.limits import (
    check_diff_limits,
    format_limit_failures,
    get_pr_diff_stats,
    limits_config_from_booty_config,
)
from booty.verifier.workspace import prepare_verification_workspace

if TYPE_CHECKING:
    from booty.jobs import JobQueue

CHECK_OUTPUT_MAX = 65535

logger = get_logger()


async def _enqueue_builder_retry(
    job: VerifierJob,
    job_queue: JobQueue,
    settings: Settings,
    summary: str,
    truncated_output: str,
) -> None:
    """Enqueue a builder retry job when verifier detects test failure on agent PR.

    Fetches the original issue from GitHub and creates a new builder Job
    with verifier_retries incremented. Only enqueues if under retry limit.
    """
    from github import Auth, Github

    try:
        # Count only completed (non-failed) retries to avoid blocking on crashes
        from booty.jobs import JobState

        completed_retries = 0
        for existing_job in job_queue.jobs.values():
            if (
                existing_job.issue_number == job.issue_number
                and existing_job.verifier_retries > 0
                and existing_job.state == JobState.COMPLETED
            ):
                completed_retries = max(
                    completed_retries, existing_job.verifier_retries
                )

        next_retry = completed_retries + 1

        if next_retry > settings.MAX_VERIFIER_RETRIES:
            logger.info(
                "verifier_retry_limit_reached",
                issue_number=job.issue_number,
                pr_number=job.pr_number,
                completed_retries=completed_retries,
                max_retries=settings.MAX_VERIFIER_RETRIES,
            )
            return

        # Fetch original issue payload from GitHub API
        auth = Auth.Token(settings.GITHUB_TOKEN)
        g = Github(auth=auth)
        repo = g.get_repo(f"{job.owner}/{job.repo_name}")
        issue = repo.get_issue(job.issue_number)

        # Build issue payload matching webhook format
        issue_payload = {
            "issue": {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body or "",
                "html_url": issue.html_url,
            },
            "repository": {
                "html_url": job.repo_url,
            },
        }

        verifier_error = f"{summary}\n\n```\n{truncated_output}\n```"

        retry_job = Job(
            job_id=f"{job.issue_number}-verifier-retry-{next_retry}",
            issue_url=issue.html_url,
            issue_number=job.issue_number,
            payload=issue_payload,
            repo_url=job.repo_url,
            verifier_retries=next_retry,
            pr_number=job.pr_number,
            verifier_error=verifier_error,
        )

        enqueued = await job_queue.enqueue(retry_job)
        if enqueued:
            logger.info(
                "verifier_retry_enqueued",
                issue_number=job.issue_number,
                pr_number=job.pr_number,
                retry=next_retry,
                max_retries=settings.MAX_VERIFIER_RETRIES,
            )
        else:
            logger.warning(
                "verifier_retry_enqueue_failed",
                issue_number=job.issue_number,
                pr_number=job.pr_number,
            )

    except Exception as e:
        logger.error(
            "verifier_retry_error",
            issue_number=job.issue_number,
            pr_number=job.pr_number,
            error=str(e),
            exc_info=True,
        )


async def process_verifier_job(
    job: VerifierJob, settings: Settings, job_queue: JobQueue | None = None
) -> None:
    """Process a verifier job: clone PR head, run tests, update check run.

    Check run lifecycle: queued → in_progress → completed (success/failure).

    Agent PRs: schema validation and diff limits run before clone (fail fast).
    """
    if not verifier_enabled(settings):
        logger.info("verifier_skipped", job_id=job.job_id, reason="verifier_disabled")
        return

    check_run = create_check_run(
        job.owner,
        job.repo_name,
        job.head_sha,
        job.installation_id,
        settings,
        status="queued",
    )
    if check_run is None:
        logger.info("verifier_skipped", job_id=job.job_id, reason="check_run_failed")
        return

    logger.info("check_created", job_id=job.job_id, status="queued")

    # Agent PRs: schema validation and diff limits before clone (fail fast)
    if job.is_agent_pr:
        repo = get_verifier_repo(
            job.owner, job.repo_name, job.installation_id, settings
        )
        if repo is not None:
            config = BootyConfig(test_command="echo 'No tests configured'")
            try:
                fc = repo.get_contents(".booty.yml", ref=job.head_sha)
                content = fc.decoded_content.decode()
                config = load_booty_config_from_content(content)
            except UnknownObjectException:
                pass
            except ValidationError as e:
                msg = str(e)[:CHECK_OUTPUT_MAX]
                edit_check_run(
                    check_run,
                    status="completed",
                    conclusion="failure",
                    output={
                        "title": "Schema validation failed",
                        "summary": msg,
                    },
                )
                logger.info("check_failed_schema", job_id=job.job_id)
                return

            limits = limits_config_from_booty_config(config)
            stats = get_pr_diff_stats(repo, job.pr_number)
            failures = check_diff_limits(stats, limits)
            if failures:
                output_text = format_limit_failures(failures)
                edit_check_run(
                    check_run,
                    status="completed",
                    conclusion="failure",
                    output={
                        "title": "Diff limits exceeded",
                        "summary": output_text[:CHECK_OUTPUT_MAX],
                    },
                )
                logger.info("check_failed_limits", job_id=job.job_id)
                return

    try:
        async with prepare_verification_workspace(
            job.repo_url,
            job.head_sha,
            settings.GITHUB_TOKEN,
            job.head_ref,
        ) as workspace:
            edit_check_run(
                check_run,
                status="in_progress",
                output={"title": "Booty Verifier", "summary": "Running tests..."},
            )
            logger.info("check_in_progress", job_id=job.job_id)

            try:
                config = load_booty_config(Path(workspace.path))
            except ValidationError as e:
                msg = str(e)[:CHECK_OUTPUT_MAX]
                edit_check_run(
                    check_run,
                    status="completed",
                    conclusion="failure",
                    output={
                        "title": "Schema validation failed",
                        "summary": msg,
                    },
                )
                logger.info("check_failed_schema", job_id=job.job_id)
                return

            workspace_path = Path(workspace.path)

            # Phase 10: setup → install → import/compile sweep → tests
            if isinstance(config, BootyConfigV1):
                if job.is_agent_pr and getattr(config, "install_command", None) in (
                    None,
                    "",
                ):
                    edit_check_run(
                        check_run,
                        status="completed",
                        conclusion="failure",
                        output={
                            "title": "Verifier failed — Config required",
                            "summary": "Config required for agent PRs: install_command.",
                        },
                    )
                    logger.info("check_failed_config", job_id=job.job_id)
                    return

                if config.setup_command:
                    setup_result = await execute_tests(
                        config.setup_command, config.timeout, workspace_path
                    )
                    if setup_result.exit_code != 0:
                        setup_annotations = parse_setup_stderr(
                            setup_result.stderr or "", workspace_path
                        )
                        ann, truncated = prepare_check_annotations(
                            setup_annotations, 50
                        )
                        summary = setup_result.stderr[:500] or "setup_command failed."
                        if truncated:
                            summary += " Too many errors — showing first 50."
                        edit_check_run(
                            check_run,
                            status="completed",
                            conclusion="failure",
                            output={
                                "title": "Verifier failed — Compile errors",
                                "summary": summary,
                                "annotations": ann,
                            },
                        )
                        logger.info("check_failed_setup", job_id=job.job_id)
                        return

                if config.install_command:
                    install_result = await execute_tests(
                        config.install_command, config.timeout, workspace_path
                    )
                    if install_result.exit_code != 0:
                        summary = (
                            (install_result.stderr or "install_command failed")[:500]
                        )
                        edit_check_run(
                            check_run,
                            status="completed",
                            conclusion="failure",
                            output={
                                "title": "Verifier failed — Install failed",
                                "summary": summary,
                            },
                        )
                        logger.info("check_failed_install", job_id=job.job_id)
                        return

            # Import/compile sweep: get changed .py files
            py_files: list[str] = []
            repo = get_verifier_repo(
                job.owner, job.repo_name, job.installation_id, settings
            )
            if repo is not None:
                stats = get_pr_diff_stats(repo, job.pr_number)
                py_files = [
                    f.filename for f in stats.files if f.filename.endswith(".py")
                ]

            if py_files:
                file_paths = [Path(f) for f in py_files]
                compile_errors = compile_sweep(file_paths, workspace_path)
                # Skip import validation for test files — they use dev deps (pytest, etc.)
                # which may not be in Booty's environment when using sys.executable
                src_paths = [p for p in file_paths if "tests" not in p.parts and not p.name.startswith("test_")]
                has_install = bool(getattr(config, "install_command", None) or "")
                import_errors = (
                    await validate_imports(src_paths, workspace_path)
                    if has_install and src_paths
                    else []
                )
                all_annotations = compile_errors + import_errors
                annotations, truncated = prepare_check_annotations(
                    all_annotations, 50
                )
                if annotations:
                    has_compile = bool(compile_errors)
                    has_import = bool(import_errors)
                    if has_compile and has_import:
                        title = "Verifier failed — Multiple failure classes"
                    elif has_compile:
                        title = "Verifier failed — Compile errors"
                    else:
                        title = "Verifier failed — Import errors"
                    n_import, n_compile = len(import_errors), len(compile_errors)
                    summary = (
                        f"{n_import} import errors, {n_compile} compile errors. "
                        "Tests not run."
                    )
                    if truncated:
                        summary += " Too many errors — showing first 50."
                    edit_check_run(
                        check_run,
                        status="completed",
                        conclusion="failure",
                        output={
                            "title": title,
                            "summary": summary,
                            "annotations": annotations,
                        },
                    )
                    logger.info("check_failed_import_compile", job_id=job.job_id)
                    return

            result = await execute_tests(
                config.test_command, config.timeout, workspace_path
            )

            tests_passed = result.exit_code == 0 and not result.timed_out

            # Agent PRs: 0 tests collected counts as failure
            # pytest exit code 5 = no tests collected
            no_tests_collected = False
            if job.is_agent_pr:
                combined_output = (result.stdout or "") + (result.stderr or "")
                if (
                    result.exit_code == 5
                    or "no tests ran" in combined_output
                    or "collected 0 items" in combined_output
                ):
                    tests_passed = False
                    no_tests_collected = True

            conclusion = "success" if tests_passed else "failure"
            if no_tests_collected:
                output_summary = (
                    "No tests collected. Agent PRs must include tests. "
                    "Add test files (e.g. tests/test_*.py) that verify the changes. "
                    "Do NOT modify .booty.yml — it is a restricted file."
                )
            else:
                output_summary = (
                    f"Tests {'passed' if tests_passed else 'failed'} (exit={result.exit_code})"
                )
            if not tests_passed and not no_tests_collected and result.stderr:
                output_summary += f". {result.stderr[:200]}"

            edit_check_run(
                check_run,
                status="completed",
                conclusion=conclusion,
                output={"title": "Booty Verifier", "summary": output_summary},
            )
            logger.info(
                "check_completed",
                job_id=job.job_id,
                conclusion=conclusion,
                tests_passed=tests_passed,
            )

            # Agent PRs: Verifier promotes on success, posts comment on failure
            if job.is_agent_pr:
                if tests_passed:
                    try:
                        promote_to_ready_for_review(
                            settings.GITHUB_TOKEN,
                            job.repo_url,
                            job.pr_number,
                        )
                        logger.info(
                            "agent_pr_promoted",
                            job_id=job.job_id,
                            pr_number=job.pr_number,
                        )
                    except Exception as e:
                        logger.warning(
                            "agent_pr_promotion_failed",
                            job_id=job.job_id,
                            pr_number=job.pr_number,
                            error=str(e),
                        )
                else:
                    stderr_lines = (result.stderr or "").splitlines()
                    truncated = "\n".join(stderr_lines[-50:])
                    post_verifier_failure_comment(
                        settings.GITHUB_TOKEN,
                        job.repo_url,
                        job.pr_number,
                        output_summary,
                        truncated,
                    )

                    # Enqueue builder retry if within retry limit
                    if job_queue is not None and job.issue_number is not None:
                        await _enqueue_builder_retry(
                            job, job_queue, settings, output_summary, truncated
                        )
    except Exception as e:
        logger.error(
            "verifier_error",
            job_id=job.job_id,
            error=str(e),
            exc_info=True,
        )
        edit_check_run(
            check_run,
            status="completed",
            conclusion="failure",
            output={
                "title": "Booty Verifier",
                "summary": f"Verifier error: {str(e)[:500]}",
            },
        )
