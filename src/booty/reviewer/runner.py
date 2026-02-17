"""Reviewer job runner — check lifecycle and LLM review integration.

Phase 38: event plumbing. Phase 39: full LLM review. Phase 41: fail-open.
"""

import asyncio
import json

from github import GithubException, UnknownObjectException
from pydantic import ValidationError

from booty.config import Settings
from booty.github.comments import post_reviewer_comment
from booty.github.checks import (
    create_reviewer_check_run,
    edit_check_run,
    get_verifier_repo,
)
from booty.logging import get_logger
from booty.reviewer.config import apply_reviewer_env_overrides, get_reviewer_config
from booty.reviewer.engine import format_reviewer_comment, run_review
from booty.reviewer.job import ReviewerJob
from booty.reviewer.metrics import (
    increment_reviewer_fail_open,
    increment_reviews_blocked,
    increment_reviews_suggestions,
    increment_reviews_total,
)
from booty.test_runner.config import load_booty_config_from_content


def _classify_fail_open_exception(exc: BaseException) -> str:
    """Classify exception into fail-open bucket for metrics and logging."""
    if isinstance(exc, UnknownObjectException):
        return "github_api_failed"
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return "llm_timeout"
    if isinstance(exc, (json.JSONDecodeError, ValidationError)):
        return "schema_parse_failed"
    if isinstance(exc, GithubException):
        return "github_api_failed"
    # Diff fetch / compare errors before run_review
    exc_name = type(exc).__name__
    if "timeout" in exc_name.lower() or "timeout" in str(exc).lower():
        return "llm_timeout"
    return "unexpected_exception"


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

    # Phase 39: fetch diff, run LLM review
    pr_payload = job.payload.get("pull_request", {})
    base_ref = pr_payload.get("base", {})
    base_sha = base_ref.get("sha", "") or job.head_sha

    try:
        compare = repo.compare(base_sha, job.head_sha)
        diff_parts: list[str] = []
        file_entries: list[str] = []
        for f in compare.files:
            if getattr(f, "patch", None):
                diff_parts.append(f.patch)
            file_type = "test" if (getattr(f, "filename", "") or "").startswith("tests/") else "src"
            file_entries.append(f"{getattr(f, 'filename', '')} ({file_type})")
        diff = "\n".join(diff_parts)
        file_list = "\n".join(file_entries) if file_entries else ""

        pr_title = pr_payload.get("title", "") or ""
        pr_body = (pr_payload.get("body") or "") or ""
        pr_meta = {
            "title": pr_title,
            "body": pr_body,
            "base_sha": base_sha,
            "head_sha": job.head_sha,
            "file_list": file_list,
        }

        result = await asyncio.to_thread(
            run_review,
            diff,
            pr_meta,
            config.block_on,
        )
    except Exception as exc:
        bucket = _classify_fail_open_exception(exc)
        increment_reviewer_fail_open(bucket)
        log = get_logger()
        log.info(
            "reviewer_fail_open",
            repo=f"{job.owner}/{job.repo_name}",
            pr=job.pr_number,
            sha=job.head_sha[:7] if job.head_sha else "",
            fail_open_type=bucket,
        )
        edit_check_run(
            check_run,
            status="completed",
            conclusion="success",
            output={
                "title": "Reviewer unavailable (fail-open)",
                "summary": "Review did not run; promotion/merge not blocked",
            },
        )
        return

    # Check conclusion per REV-05
    if result.decision == "APPROVED":
        conclusion = "success"
        title = "Reviewer approved"
    elif result.decision == "APPROVED_WITH_SUGGESTIONS":
        conclusion = "success"
        title = "Reviewer approved with suggestions"
    else:
        conclusion = "failure"
        title = "Reviewer blocked"

    summary = "See PR comment for details."
    if result.blocking_categories:
        summary = f"Blocking: {', '.join(result.blocking_categories)}"

    edit_check_run(
        check_run,
        status="completed",
        conclusion=conclusion,
        output={"title": title, "summary": summary},
    )

    body = format_reviewer_comment(result)
    post_reviewer_comment(settings.GITHUB_TOKEN, job.repo_url, job.pr_number, body)

    # Metrics and structured log (REV-15)
    increment_reviews_total()
    if result.decision == "APPROVED_WITH_SUGGESTIONS":
        increment_reviews_suggestions()
    elif result.decision == "BLOCKED":
        increment_reviews_blocked()

    suggestion_count = sum(
        1
        for c in result.categories
        for f in c.findings
        if f.suggestion
    )
    log = get_logger()
    log.info(
        "reviewer_outcome",
        repo=f"{job.owner}/{job.repo_name}",
        pr=job.pr_number,
        sha=job.head_sha[:7] if job.head_sha else "",
        outcome=result.decision,
        blocked_categories=result.blocking_categories or [],
        suggestion_count=suggestion_count,
    )
