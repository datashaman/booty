"""GitHub webhook handler with HMAC verification."""

import hmac
import hashlib
import json
import os
import re
import time
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse

from github import Github

from booty.config import get_settings
from booty.router import route_github_event
from booty.github.issues import create_sentry_issue_with_retry
from booty.github.repo_config import load_booty_config_for_repo, repo_from_url
from booty.memory.surfacing import build_related_history_for_incident, surface_pr_comment
from booty.memory import add_record, get_memory_config
from booty.memory.adapters import build_incident_record, build_revert_record
from booty.memory.config import apply_memory_env_overrides
from booty.logging import get_logger


router = APIRouter(prefix="/webhooks")

# In-memory cooldown: issue_id -> last_created_ts
_obsv_seen: dict[str, float] = {}


def _cleanup_cooldown() -> None:
    """Remove expired entries from cooldown dictionary to prevent unbounded growth."""
    settings = get_settings()
    now = time.time()
    window_sec = settings.OBSV_COOLDOWN_HOURS * 3600
    # Remove entries older than 2x the cooldown window
    expired = [k for k, v in _obsv_seen.items() if (now - v) > window_sec * 2]
    for k in expired:
        del _obsv_seen[k]
    if expired:
        logger = get_logger()
        logger.debug("cooldown_cleanup", removed_count=len(expired))


def _severity_rank(level: str) -> int:
    """Return numeric rank for severity (lower = more severe). Filter pass when rank <= min rank."""
    return {
        "fatal": 0,
        "error": 1,
        "warning": 2,
        "info": 3,
        "debug": 4,
    }.get(level.lower(), 99)


def verify_sentry_signature(
    payload_body: bytes, secret: str, sig_header: str | None
) -> None:
    """Verify Sentry webhook HMAC-SHA256 signature.

    Args:
        payload_body: Raw request body bytes
        secret: Webhook secret from SENTRY_WEBHOOK_SECRET
        sig_header: Sentry-Hook-Signature header value

    Raises:
        HTTPException: 401 if signature missing or mismatch
    """
    if not sig_header:
        raise HTTPException(status_code=401, detail="invalid_signature")
    expected = hmac.new(
        secret.encode("utf-8"), payload_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig_header):
        raise HTTPException(status_code=401, detail="invalid_signature")


def verify_signature(
    payload_body: bytes, secret: str, signature_header: str | None
) -> None:
    """Verify GitHub webhook HMAC signature.

    Args:
        payload_body: Raw request body bytes
        secret: Webhook secret
        signature_header: X-Hub-Signature-256 header value

    Raises:
        HTTPException: 401 if signature missing, 403 if verification fails
    """
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature header")

    # Compute expected signature
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), payload_body, hashlib.sha256
    ).hexdigest()

    # Constant-time comparison
    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=403, detail="Invalid signature")


@router.post("/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle GitHub webhook events.

    Verifies HMAC signature, filters for labeled issues, deduplicates
    based on delivery ID, and enqueues jobs.

    Returns:
        dict: Status response
    """
    logger = get_logger()
    settings = get_settings()

    # Read raw body BEFORE any JSON parsing (critical for HMAC)
    payload_body = await request.body()

    # Get headers
    signature_header = request.headers.get("X-Hub-Signature-256")
    delivery_id = request.headers.get("X-GitHub-Delivery")
    event_type = request.headers.get("X-GitHub-Event")

    # Verify signature
    verify_signature(payload_body, settings.WEBHOOK_SECRET, signature_header)
    logger.info("signature_verified", delivery_id=delivery_id, event_type=event_type)

    # Parse payload
    payload = await request.json()

    # Handle check_run events (Memory PR comment on Verifier completion)
    if event_type == "check_run":
        action = payload.get("action")
        if action != "completed":
            return {"status": "ignored", "reason": "check_not_completed"}
        check_run = payload.get("check_run", {})
        if check_run.get("name") != "booty/verifier":
            return {"status": "ignored"}
        pull_requests = check_run.get("pull_requests", [])
        if not pull_requests:
            return {"status": "ignored", "reason": "no_pr"}
        pr_ref = pull_requests[0]
        pr_number = pr_ref.get("number") if isinstance(pr_ref, dict) else getattr(pr_ref, "number", None)
        if not pr_number:
            return {"status": "ignored", "reason": "no_pr_number"}
        repo = payload.get("repository", {})
        repo_full_name = repo.get("full_name", "")
        repo_url = repo.get("html_url", "") or f"https://github.com/{repo_full_name}"
        try:
            booty_config = load_booty_config_for_repo(repo_url, settings.GITHUB_TOKEN)
            mem_config = get_memory_config(booty_config) if booty_config else None
            if mem_config:
                mem_config = apply_memory_env_overrides(mem_config)
            if not mem_config or not mem_config.enabled or not mem_config.comment_on_pr:
                return {"status": "ignored", "reason": "memory_disabled"}
            g = Github(settings.GITHUB_TOKEN)
            gh_repo = g.get_repo(repo_full_name)
            pr = gh_repo.get_pull(pr_number)
            paths = [f.filename for f in pr.get_files()]
            surface_pr_comment(
                settings.GITHUB_TOKEN,
                repo_url,
                pr_number,
                paths,
                repo_full_name,
                mem_config,
            )
            return JSONResponse(
                status_code=202,
                content={"status": "accepted", "event": "check_run", "memory_surfaced": True},
            )
        except Exception as e:
            logger.warning(
                "memory_surfacing_failed",
                pr_number=pr_number,
                error=str(e),
            )
            return JSONResponse(
                status_code=202,
                content={"status": "accepted", "event": "check_run", "memory_surfaced": False, "error": str(e)},
            )

    # Handle pull_request events (Verifier + Security + Reviewer) — delegated to router
    if event_type == "pull_request":
        result = await route_github_event(
            event_type, payload, delivery_id, request.app.state
        )
        if result.get("status") == "accepted":
            return JSONResponse(status_code=202, content=result)
        return result

    # Handle workflow_run events (Release Governor) — delegated to router
    if event_type == "workflow_run":
        result = await route_github_event(
            event_type,
            payload,
            delivery_id,
            request.app.state,
            background_tasks=background_tasks,
        )
        if result.get("status") == "accepted":
            return JSONResponse(status_code=202, content=result)
        return result

    # Handle push events (revert detection on main)
    if event_type == "push":
        ref = payload.get("ref", "")
        if ref != "refs/heads/main":
            logger.info(
                "event_filtered",
                event_type=event_type,
                reason="not_main",
            )
            return {"status": "ignored", "reason": "not_main"}
        repo = payload.get("repository", {})
        repo_full_name = repo.get("full_name", "")
        commits = payload.get("commits", [])
        revert_pattern = re.compile(r"(?i)revert\s+[\"\']?([a-f0-9]{7,40})[\"\']?")
        for commit in commits:
            message = commit.get("message", "")
            sha = commit.get("id", "") or commit.get("sha", "")
            match = revert_pattern.search(message)
            if match:
                reverted_sha = match.group(1)
                try:
                    booty_config = load_booty_config_for_repo(
                        f"https://github.com/{repo_full_name}",
                        settings.GITHUB_TOKEN,
                    )
                    mem_config = get_memory_config(booty_config) if booty_config else None
                    if mem_config:
                        mem_config = apply_memory_env_overrides(mem_config)
                    if mem_config and mem_config.enabled:
                        record = build_revert_record(
                            repo_full_name, sha, reverted_sha, source="push"
                        )
                        add_record(record, mem_config)
                except Exception as e:
                    logger.warning(
                        "memory_ingestion_failed",
                        type="revert",
                        error=str(e),
                    )
        return JSONResponse(
            status_code=202,
            content={"status": "accepted", "event": "push"},
        )

    # Handle issues events — delegated to router
    if event_type == "issues":
        result = await route_github_event(
            event_type,
            payload,
            delivery_id,
            request.app.state,
            background_tasks=background_tasks,
        )
        if result.get("status") == "accepted":
            return JSONResponse(status_code=202, content=result)
        if result.get("status") == "error":
            return JSONResponse(status_code=503, content=result)
        return result

    logger.info("event_filtered", event_type=event_type, reason="not_handled")
    return {"status": "ignored", "reason": "not_handled"}


@router.post("/sentry")
async def sentry_webhook(request: Request):
    """Handle Sentry event_alert webhooks.

    Verifies HMAC-SHA256, filters by resource/severity/cooldown, and returns
    status. Issue creation is delegated to Plan 02.
    """
    logger = get_logger()
    settings = get_settings()

    payload_body = await request.body()
    sig_header = (
        request.headers.get("Sentry-Hook-Signature")
        or request.headers.get("sentry-hook-signature")
    )

    # Only verify signature if webhook secret is configured
    if settings.SENTRY_WEBHOOK_SECRET:
        try:
            verify_sentry_signature(payload_body, settings.SENTRY_WEBHOOK_SECRET, sig_header)
        except HTTPException:
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_signature"},
            )
    else:
        logger.warning("sentry_webhook_verification_disabled", reason="no_secret_configured")

    resource = request.headers.get("Sentry-Hook-Resource")
    if resource != "event_alert":
        return {"status": "ignored", "reason": "not_event_alert"}

    try:
        payload = json.loads(payload_body)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=422,
            content={"error": "invalid_payload", "missing": ["valid_json"]},
        )

    if payload.get("action") != "triggered":
        return {"status": "ignored", "reason": "not_triggered"}

    data = payload.get("data", {})
    event = data.get("event")
    if not event:
        return JSONResponse(
            status_code=422,
            content={"error": "invalid_payload", "missing": ["data.event"]},
        )

    issue_id = event.get("issue_id")
    level = event.get("level", "error")

    # Normalize issue_id to string and validate it's not empty
    missing = []
    if issue_id is None or (isinstance(issue_id, str) and not issue_id.strip()):
        missing.append("issue_id")
    else:
        issue_id = str(issue_id)  # Normalize to string for consistent dictionary keys
    if not level:
        missing.append("level")
    if missing:
        return JSONResponse(
            status_code=422,
            content={"error": "invalid_payload", "missing": missing},
        )

    if _severity_rank(level) > _severity_rank(settings.OBSV_MIN_SEVERITY):
        return {"status": "ignored", "reason": "below_threshold"}

    # Clean up expired cooldown entries periodically
    _cleanup_cooldown()

    now = time.time()
    window_sec = settings.OBSV_COOLDOWN_HOURS * 3600
    if issue_id in _obsv_seen and (now - _obsv_seen[issue_id]) < window_sec:
        return {"status": "ignored", "reason": "cooldown"}

    related_history = ""
    booty_config = load_booty_config_for_repo(
        settings.TARGET_REPO_URL, settings.GITHUB_TOKEN
    )
    mem_config = get_memory_config(booty_config) if booty_config else None
    if mem_config:
        mem_config = apply_memory_env_overrides(mem_config)
    if mem_config and mem_config.enabled and mem_config.comment_on_incident_issue:
        related_history = build_related_history_for_incident(
            event,
            repo_from_url(settings.TARGET_REPO_URL),
            mem_config,
        )

    issue_number = create_sentry_issue_with_retry(
        event,
        settings.GITHUB_TOKEN,
        settings.TARGET_REPO_URL,
        settings.TRIGGER_LABEL,
        related_history=related_history,
    )
    if issue_number is not None:
        _obsv_seen[issue_id] = now
        # Memory ingestion when enabled
        booty_config = load_booty_config_for_repo(
            settings.TARGET_REPO_URL, settings.GITHUB_TOKEN
        )
        mem_config = get_memory_config(booty_config) if booty_config else None
        if mem_config:
            mem_config = apply_memory_env_overrides(mem_config)
        if mem_config and mem_config.enabled:
            try:
                repo = repo_from_url(settings.TARGET_REPO_URL)
                record = build_incident_record(event, issue_number, repo)
                add_record(record, mem_config)
            except Exception as e:
                logger.warning(
                    "memory_ingestion_failed",
                    type="incident",
                    error=str(e),
                )
        logger.info(
            "observability_issue_created",
            issue_id=issue_id,
            issue_number=issue_number,
        )
        return JSONResponse(
            status_code=202,
            content={"status": "created", "issue_number": issue_number, "issue_id": issue_id},
        )
    logger.warning("observability_issue_spooled", issue_id=issue_id)
    return JSONResponse(
        status_code=202,
        content={"status": "spooled", "issue_id": issue_id},
    )
