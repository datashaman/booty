"""Security job runner — check lifecycle and config loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

from github import UnknownObjectException

from booty.config import Settings, security_enabled
from booty.github.checks import (
    create_security_check_run,
    edit_check_run,
    get_verifier_repo,
)
from booty.logging import get_logger
from booty.test_runner.config import (
    BootyConfigV1,
    apply_security_env_overrides,
    load_booty_config_from_content,
)

from booty.security.job import SecurityJob

if TYPE_CHECKING:
    pass

logger = get_logger()


async def process_security_job(job: SecurityJob, settings: Settings) -> None:
    """Process a security job: create check, load config, complete.

    Check run lifecycle: queued → in_progress → completed (success).
    Phase 18 baseline: no actual scanning; load config and complete success.
    """
    if not security_enabled(settings):
        logger.info(
            "security_skipped",
            job_id=job.job_id,
            reason="security_disabled",
        )
        return

    check_run = create_security_check_run(
        job.owner,
        job.repo_name,
        job.head_sha,
        job.installation_id,
        settings,
        status="queued",
    )
    if check_run is None:
        logger.info(
            "security_skipped",
            job_id=job.job_id,
            reason="check_run_failed",
        )
        return

    logger.info("security_check_created", job_id=job.job_id, status="queued")

    edit_check_run(
        check_run,
        status="in_progress",
        output={
            "title": "Booty Security",
            "summary": "Scanning for secrets and vulnerabilities…",
        },
    )
    logger.info("security_check_in_progress", job_id=job.job_id)

    # Load config from repo
    security_config = None
    repo = get_verifier_repo(
        job.owner,
        job.repo_name,
        job.installation_id,
        settings,
    )
    if repo is not None:
        try:
            fc = repo.get_contents(".booty.yml", ref=job.head_sha)
            content = fc.decoded_content.decode()
            config = load_booty_config_from_content(content)
            if isinstance(config, BootyConfigV1) and config.security is not None:
                security_config = apply_security_env_overrides(config.security)
        except UnknownObjectException:
            # No .booty.yml — treat as Security enabled (default)
            security_config = None
        except Exception as e:
            logger.warning(
                "security_config_load_failed",
                job_id=job.job_id,
                error=str(e),
            )

    # Phase 18: if security disabled or not configured, complete success
    if security_config is not None and not security_config.enabled:
        edit_check_run(
            check_run,
            status="completed",
            conclusion="success",
            output={
                "title": "Security check complete",
                "summary": "Security check complete — disabled",
            },
        )
        logger.info("security_check_completed", job_id=job.job_id, conclusion="success")
        return

    # Security enabled (or default): Phase 18 baseline — no scanners yet
    edit_check_run(
        check_run,
        status="completed",
        conclusion="success",
        output={
            "title": "Security check complete",
            "summary": "Security check complete — no scanners configured",
        },
    )
    logger.info("security_check_completed", job_id=job.job_id, conclusion="success")
