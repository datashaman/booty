"""Verifier job runner — clone, test, update check run."""

from pathlib import Path

from github import UnknownObjectException
from pydantic import ValidationError

from booty.config import Settings, verifier_enabled
from booty.github.checks import create_check_run, edit_check_run, get_verifier_repo
from booty.github.comments import post_verifier_failure_comment
from booty.github.promotion import promote_to_ready_for_review
from booty.logging import get_logger
from booty.test_runner.config import BootyConfig, load_booty_config, load_booty_config_from_content
from booty.test_runner.executor import execute_tests

from booty.verifier.job import VerifierJob
from booty.verifier.limits import (
    check_diff_limits,
    format_limit_failures,
    get_pr_diff_stats,
    limits_config_from_booty_config,
)
from booty.verifier.workspace import prepare_verification_workspace

CHECK_OUTPUT_MAX = 65535

logger = get_logger()


async def process_verifier_job(job: VerifierJob, settings: Settings) -> None:
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

            result = await execute_tests(
                config.test_command, config.timeout, Path(workspace.path)
            )

            tests_passed = result.exit_code == 0 and not result.timed_out
            conclusion = "success" if tests_passed else "failure"
            output_summary = (
                f"Tests {'passed' if tests_passed else 'failed'} (exit={result.exit_code})"
            )
            if not tests_passed and result.stderr:
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
