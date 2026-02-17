"""Reviewer job runner — check lifecycle and stub success.

Phase 38: event plumbing only. Phase 39 adds LLM review.
"""

from github import UnknownObjectException

from booty.config import Settings
from booty.github.checks import (
    create_reviewer_check_run,
    edit_check_run,
    get_verifier_repo,
)
from booty.reviewer.config import apply_reviewer_env_overrides, get_reviewer_config
from booty.reviewer.job import ReviewerJob
from booty.test_runner.config import load_booty_config_from_content


async def process_reviewer_job(job: ReviewerJob, settings: Settings) -> None:
    """Process Reviewer job — Phase 38 stub: check lifecycle only. Phase 39 adds LLM."""

    if getattr(job, "cancel_event", None) and job.cancel_event.is_set():
        return

    repo = get_verifier_repo(
        job.owner,
        job.repo_name,
        job.installation_id,
        settings,
    )
    if repo is None:
        return

    try:
        fc = repo.get_contents(".booty.yml", ref=job.head_sha)
        content = fc.decoded_content.decode("utf-8")
        booty_config = load_booty_config_from_content(content)
    except UnknownObjectException:
        booty_config = None
    except Exception:
        booty_config = None

    config = get_reviewer_config(booty_config) if booty_config else None
    if config is None:
        return

    config = apply_reviewer_env_overrides(config)
    if not config.enabled:
        return

    if getattr(job, "cancel_event", None) and job.cancel_event.is_set():
        return

    check_run = create_reviewer_check_run(
        job.owner,
        job.repo_name,
        job.head_sha,
        job.installation_id,
        settings,
        status="queued",
        output={"title": "Booty Reviewer", "summary": "Queued for review…"},
    )
    if check_run is None:
        return

    edit_check_run(
        check_run,
        status="in_progress",
        output={"title": "Booty Reviewer", "summary": "In progress…"},
    )

    if getattr(job, "cancel_event", None) and job.cancel_event.is_set():
        edit_check_run(
            check_run,
            status="completed",
            conclusion="cancelled",
            output={"title": "Booty Reviewer", "summary": "Cancelled — superseded by new push"},
        )
        return

    edit_check_run(
        check_run,
        status="completed",
        conclusion="success",
        output={
            "title": "Reviewer approved",
            "summary": "Review complete (stub). Phase 39 adds LLM.",
        },
    )
