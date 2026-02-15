"""Verifier job runner — clone, test, update check run."""

from pathlib import Path

from booty.config import Settings, verifier_enabled
from booty.github.checks import create_check_run, edit_check_run
from booty.logging import get_logger
from booty.test_runner.config import load_booty_config
from booty.test_runner.executor import execute_tests

from booty.verifier.job import VerifierJob
from booty.verifier.workspace import prepare_verification_workspace

logger = get_logger()


async def process_verifier_job(job: VerifierJob, settings: Settings) -> None:
    """Process a verifier job: clone PR head, run tests, update check run.

    Check run lifecycle: queued → in_progress → completed (success/failure).
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

            config = load_booty_config(Path(workspace.path))
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
