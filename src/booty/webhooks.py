"""GitHub webhook handler with HMAC verification."""

import hmac
import hashlib
import json
import os
import re
import time
from urllib.parse import urlparse

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse

from github import Github

from booty.config import get_settings, planner_enabled, security_enabled, verifier_enabled
from booty.release_governor.deploy import dispatch_deploy
from booty.release_governor.failure_issues import create_or_append_deploy_failure_issue
from booty.release_governor.handler import handle_workflow_run
from booty.release_governor.store import (
    append_deploy_to_history,
    get_state_dir,
    has_delivery_id,
    load_release_state,
    record_delivery_id,
    save_release_state,
)
from booty.release_governor.ux import post_allow_status, post_hold_status
from booty.test_runner.config import (
    apply_release_governor_env_overrides,
    load_booty_config_from_content,
)
from booty.github.issues import create_sentry_issue_with_retry
from booty.github.comments import post_builder_blocked_comment, post_self_modification_disabled_comment
from booty.memory.surfacing import (
    build_related_history_for_incident,
    surface_governor_hold,
    surface_pr_comment,
)
from booty.memory import add_record, get_memory_config
from booty.memory.adapters import (
    build_deploy_failure_record,
    build_governor_hold_record,
    build_incident_record,
    build_revert_record,
)
from booty.memory.config import apply_memory_env_overrides
from booty.jobs import Job
from booty.planner.jobs import PlannerJob, planner_enqueue, planner_is_duplicate, planner_mark_processed
from booty.planner.store import load_plan, plan_path_for_issue
from booty.logging import get_logger
from booty.self_modification.detector import is_self_modification
from booty.security import SecurityJob
from booty.verifier import VerifierJob


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


def _repo_from_url(repo_url: str) -> str:
    """Parse owner/repo from GitHub URL (https://github.com/o/r or git@github.com:o/r.git)."""
    if not repo_url:
        return ""
    # git@github.com:owner/repo.git
    if repo_url.startswith("git@"):
        part = repo_url.split(":")[-1].rstrip("/").removesuffix(".git")
        return part
    # https://github.com/owner/repo or https://github.com/owner/repo.git
    parsed = urlparse(repo_url)
    path = (parsed.path or "").lstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path


def _load_booty_config_for_repo(repo_url: str, gh_token: str):
    """Load BootyConfig from repo .booty.yml. Returns None on any error."""
    logger = get_logger()
    try:
        owner_repo = _repo_from_url(repo_url)
        if not owner_repo or "/" not in owner_repo:
            return None
        g = Github(gh_token)
        repo = g.get_repo(owner_repo)
        fc = repo.get_contents(".booty.yml", ref=repo.default_branch or "main")
        content = fc.decoded_content.decode("utf-8")
        return load_booty_config_from_content(content)
    except Exception as e:
        logger.warning("booty_config_load_failed", repo_url=repo_url, error=str(e))
        return None


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
            booty_config = _load_booty_config_for_repo(repo_url, settings.GITHUB_TOKEN)
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

    # Handle pull_request events (Verifier + Security)
    if event_type == "pull_request":
        verifier_queue = getattr(request.app.state, "verifier_queue", None)
        security_queue = getattr(request.app.state, "security_queue", None)
        verifier_ok = verifier_queue is not None and verifier_enabled(settings)
        security_ok = security_queue is not None and security_enabled(settings)
        if not verifier_ok and not security_ok:
            logger.info(
                "event_filtered",
                event_type=event_type,
                reason="verifier_and_security_disabled",
            )
            return {"status": "ignored", "reason": "verifier_and_security_disabled"}

        action = payload.get("action")
        if action not in ("opened", "synchronize", "reopened"):
            logger.info(
                "event_filtered",
                event_type=event_type,
                action=action,
                reason="unhandled_action",
            )
            return {"status": "ignored"}

        repo = payload.get("repository", {})
        pr = payload.get("pull_request", {})
        owner = repo.get("owner", {}).get("login", "")
        repo_name = repo.get("name", "")
        pr_number = pr.get("number", 0)
        head_sha = pr.get("head", {}).get("sha", "")
        head_ref = pr.get("head", {}).get("ref", "")
        repo_url = repo.get("html_url", "")
        installation_id = payload.get("installation", {}).get("id") or 0
        labels = [l.get("name", "") for l in pr.get("labels", [])]
        is_agent_pr = (
            settings.TRIGGER_LABEL in labels
            or pr.get("user", {}).get("type") == "Bot"
            or head_ref.startswith("agent/issue-")
        )

        if not head_sha:
            logger.warning("pull_request_missing_head_sha", pr_number=pr_number)
            return {"status": "ignored", "reason": "missing_head_sha"}

        # Verifier enqueue
        verifier_enqueued = False
        verifier_job_id = None
        if verifier_ok:
            if verifier_queue.is_duplicate(pr_number, head_sha):
                logger.info(
                    "verifier_already_processed",
                    pr_number=pr_number,
                    head_sha=head_sha[:7],
                )
            else:
                issue_number_from_branch = None
                branch_match = re.match(r"^agent/issue-(\d+)$", head_ref)
                if branch_match:
                    issue_number_from_branch = int(branch_match.group(1))

                verifier_job_id = f"verifier-{pr_number}-{head_sha[:7]}"
                job = VerifierJob(
                    job_id=verifier_job_id,
                    owner=owner,
                    repo_name=repo_name,
                    pr_number=pr_number,
                    head_sha=head_sha,
                    head_ref=head_ref,
                    repo_url=repo_url,
                    installation_id=installation_id,
                    payload=payload,
                    is_agent_pr=is_agent_pr,
                    issue_number=issue_number_from_branch,
                )
                enqueued = await verifier_queue.enqueue(job)
                if enqueued:
                    verifier_enqueued = True
                    logger.info(
                        "verifier_job_accepted",
                        job_id=verifier_job_id,
                        pr_number=pr_number,
                    )
                else:
                    logger.error("verifier_enqueue_failed", job_id=verifier_job_id)

        # Security enqueue (runs on every PR, separate queue)
        security_enqueued = False
        security_job_id = None
        if security_ok and not security_queue.is_duplicate(pr_number, head_sha):
            security_job_id = f"security-{pr_number}-{head_sha[:7]}"
            base = pr.get("base", {})
            base_sha = base.get("sha", "") or ""
            base_ref = base.get("ref", "") or "main"
            sec_job = SecurityJob(
                job_id=security_job_id,
                owner=owner,
                repo_name=repo_name,
                pr_number=pr_number,
                head_sha=head_sha,
                head_ref=head_ref,
                base_sha=base_sha,
                base_ref=base_ref,
                repo_url=repo_url,
                installation_id=installation_id,
                payload=payload,
            )
            if await security_queue.enqueue(sec_job):
                security_enqueued = True
                logger.info(
                    "security_job_accepted",
                    job_id=security_job_id,
                    pr_number=pr_number,
                )
            else:
                logger.error("security_enqueue_failed", job_id=security_job_id)

        if verifier_enqueued or security_enqueued:
            job_id = verifier_job_id if verifier_enqueued else security_job_id
            return JSONResponse(
                status_code=202,
                content={"status": "accepted", "job_id": job_id},
            )

        # Both duplicate or failed to enqueue
        if verifier_ok:
            return {"status": "already_processed"}
        if security_ok:
            return {"status": "already_processed"}
        return {"status": "ignored"}

    # Handle workflow_run events (Release Governor)
    if event_type == "workflow_run":
        action = payload.get("action")
        wr = payload.get("workflow_run", {})
        conclusion = wr.get("conclusion")
        workflow_name = wr.get("name", "")
        workflow_path = wr.get("path") or wr.get("workflow", {}).get("path", "")
        head_sha = wr.get("head_sha", "")
        head_branch = wr.get("head_branch", "")
        repo = payload.get("repository", {})
        repo_full_name = repo.get("full_name", "")

        if action != "completed":
            logger.info(
                "event_filtered",
                event_type=event_type,
                reason="workflow_not_completed",
                action=action,
            )
            return {"status": "ignored", "reason": "workflow_not_completed"}

        # Load config from repo .booty.yml
        try:
            gh = Github(settings.GITHUB_TOKEN)
            gh_repo = gh.get_repo(repo_full_name)
            default_branch = gh_repo.default_branch or "main"
            fc = gh_repo.get_contents(".booty.yml", ref=default_branch)
            yaml_content = fc.decoded_content.decode("utf-8")
            config = load_booty_config_from_content(yaml_content)
            governor_config = apply_release_governor_env_overrides(
                config.release_governor
            ) if getattr(config, "release_governor", None) else None
        except Exception:
            governor_config = None

        if not governor_config or not governor_config.enabled:
            logger.info(
                "event_filtered",
                event_type=event_type,
                reason="governor_disabled",
            )
            return {"status": "ignored", "reason": "governor_disabled"}

        # Branch by workflow identity: deploy outcome first, then verification
        is_deploy = (
            (workflow_path or "").endswith(governor_config.deploy_workflow_name)
            or workflow_name == governor_config.deploy_workflow_name
        )
        is_verification = workflow_name == governor_config.verification_workflow_name

        if is_deploy:
            # Deploy outcome observation (GOV-16, GOV-17)
            state_dir = get_state_dir()
            wr_id = wr.get("id") or wr.get("run_id") or ""
            deploy_run_key = f"deploy_run_{wr_id}" if wr_id else f"deploy_run_{head_sha}"
            if has_delivery_id(state_dir, repo_full_name, deploy_run_key):
                logger.info(
                    "governor_deploy_outcome_already_processed",
                    repo=repo_full_name,
                    head_sha=head_sha[:7] if head_sha else "?",
                )
                return {"status": "already_processed"}

            now_iso = datetime.now(timezone.utc).isoformat()
            state = load_release_state(state_dir)
            if conclusion == "success":
                state.production_sha_previous = state.production_sha_current
                state.production_sha_current = head_sha
                state.last_deploy_attempt_sha = head_sha
                state.last_deploy_time = now_iso
                state.last_deploy_result = "success"
                save_release_state(state_dir, state)
                append_deploy_to_history(state_dir, head_sha, now_iso, "success")
            elif conclusion in ("failure", "cancelled"):
                failure_type = (
                    "deploy:cancelled" if conclusion == "cancelled"
                    else "deploy:health-check-failed"
                )
                run_url = wr.get("html_url", "") or wr.get("url", "") or ""
                create_or_append_deploy_failure_issue(
                    gh_repo, head_sha, run_url, conclusion, failure_type
                )
                # Memory ingestion for deploy failure
                mem_config = get_memory_config(config) if config else None
                if mem_config:
                    mem_config = apply_memory_env_overrides(mem_config)
                if mem_config and mem_config.enabled:
                    try:
                        record = build_deploy_failure_record(
                            head_sha, run_url, conclusion, failure_type, repo_full_name
                        )
                        add_record(record, mem_config)
                    except Exception as e:
                        logger.warning(
                            "memory_ingestion_failed",
                            type="deploy_failure",
                            error=str(e),
                        )
                state.last_deploy_attempt_sha = head_sha
                state.last_deploy_time = now_iso
                state.last_deploy_result = "failure"
                save_release_state(state_dir, state)
                append_deploy_to_history(state_dir, head_sha, now_iso, "failure")
            else:
                # skipped, etc. — update state only
                state.last_deploy_attempt_sha = head_sha
                state.last_deploy_time = now_iso
                state.last_deploy_result = conclusion or "skipped"
                save_release_state(state_dir, state)
                append_deploy_to_history(state_dir, head_sha, now_iso, conclusion or "skipped")

            if delivery_id:
                record_delivery_id(state_dir, repo_full_name, deploy_run_key, delivery_id)

            logger.info(
                "governor_deploy_outcome_processed",
                repo=repo_full_name,
                head_sha=head_sha[:7] if head_sha else "?",
                conclusion=conclusion,
            )
            return JSONResponse(
                status_code=202,
                content={
                    "status": "accepted",
                    "event": "workflow_run",
                    "type": "deploy_outcome",
                    "conclusion": conclusion,
                },
            )

        if is_verification and conclusion == "success" and head_branch == "main":
            # Verification workflow success -> decision pipeline (GOV-01, GOV-14, GOV-15)
            state_dir = get_state_dir()
            if has_delivery_id(state_dir, repo_full_name, head_sha):
                logger.info(
                    "governor_already_processed",
                    repo=repo_full_name,
                    head_sha=head_sha[:7],
                )
                return {"status": "already_processed"}

            decision = handle_workflow_run(payload, governor_config)

            html_url = repo.get("html_url", "") or ""
            actions_url = f"{html_url.rstrip('/')}/actions" if html_url else ""
            default_branch = gh_repo.default_branch or "main"
            hold_docs_url = (
                f"{html_url.rstrip('/')}/blob/{default_branch}/docs/release-governor.md"
                if html_url
                else ""
            )

            if decision.outcome == "ALLOW":
                dispatch_deploy(gh_repo, governor_config, head_sha)
                now_iso = datetime.now(timezone.utc).isoformat()
                state = load_release_state(state_dir)
                state.last_deploy_attempt_sha = head_sha
                state.last_deploy_time = now_iso
                state.last_deploy_result = "pending"
                save_release_state(state_dir, state)
                append_deploy_to_history(state_dir, head_sha, now_iso, "pending")
                post_allow_status(gh_repo, head_sha, actions_url)
            else:
                approval_hint = None
                if decision.reason == "high_risk_no_approval":
                    mode = governor_config.approval_mode
                    if mode == "label" and governor_config.approval_label:
                        approval_hint = f"Approval via label: {governor_config.approval_label}"
                    elif mode == "comment" and governor_config.approval_command:
                        approval_hint = f"Approval via comment: {governor_config.approval_command}"
                    elif mode == "environment":
                        approval_hint = "Approval via env: RELEASE_GOVERNOR_APPROVED=true"
                post_hold_status(gh_repo, head_sha, decision, hold_docs_url, approval_hint)
                # Memory surfacing for Governor HOLD (1-2 hold-reason matches in PR comment)
                mem_config = get_memory_config(config) if config else None
                if mem_config:
                    mem_config = apply_memory_env_overrides(mem_config)
                if mem_config and mem_config.enabled and mem_config.comment_on_pr:
                    background_tasks.add_task(
                        surface_governor_hold,
                        settings.GITHUB_TOKEN,
                        repo_full_name,
                        head_sha,
                        decision.reason,
                        mem_config,
                    )
                # Memory ingestion for Governor HOLD
                if mem_config and mem_config.enabled:
                    try:
                        record = build_governor_hold_record(decision, repo_full_name)
                        add_record(record, mem_config)
                    except Exception as e:
                        logger.warning(
                            "memory_ingestion_failed",
                            type="governor_hold",
                            error=str(e),
                        )

            if delivery_id:
                record_delivery_id(state_dir, repo_full_name, head_sha, delivery_id)

            logger.info(
                "governor_workflow_processed",
                repo=repo_full_name,
                head_sha=head_sha[:7],
                outcome=decision.outcome,
                reason=decision.reason,
            )
            return JSONResponse(
                status_code=202,
                content={"status": "accepted", "event": "workflow_run", "outcome": decision.outcome},
            )

        logger.info(
            "event_filtered",
            event_type=event_type,
            reason="workflow_not_matched",
            workflow_name=workflow_name,
        )
        return {"status": "ignored", "reason": "workflow_not_matched"}

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
                    booty_config = _load_booty_config_for_repo(
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

    # Handle issues events — Planner-first architecture
    # Flow: Planner is single work originator; Builder only runs when plan exists
    if event_type != "issues":
        logger.info("event_filtered", event_type=event_type, reason="not_issues")
        return {"status": "ignored"}

    action = payload.get("action")
    issue = payload.get("issue", {})
    labels = [l.get("name", "") for l in issue.get("labels", [])]
    repo_info = payload.get("repository", {})
    owner = repo_info.get("owner", {}).get("login", "")
    repo_name = repo_info.get("name", "")
    full_name = repo_info.get("full_name", "")
    repo_url = repo_info.get("html_url", "") or f"https://github.com/{full_name or 'unknown'}"
    issue_number = issue.get("number", 0)

    # Planner triggers: agent:plan on opened or labeled
    is_plan_trigger = (
        planner_enabled(settings)
        and (
            (action == "opened" and "agent:plan" in labels)
            or (action == "labeled" and payload.get("label", {}).get("name") == "agent:plan")
        )
    )
    if is_plan_trigger:
        if delivery_id and planner_is_duplicate(delivery_id):
            logger.info("planner_already_processed", delivery_id=delivery_id)
            return {"status": "already_processed"}
        job_id = f"planner-{issue_number}-{delivery_id or 'no-delivery'}"
        job = PlannerJob(
            job_id=job_id,
            issue_number=issue_number,
            issue_url=issue.get("html_url", ""),
            repo_url=repo_url,
            owner=owner,
            repo=repo_name,
            payload=payload,
        )
        enqueued = await planner_enqueue(job)
        if not enqueued:
            logger.error("planner_enqueue_failed", job_id=job_id)
            return JSONResponse(
                status_code=503,
                content={"status": "error", "event": "planner", "reason": "enqueue_failed"},
            )
        if delivery_id:
            planner_mark_processed(delivery_id)
        logger.info("planner_job_accepted", job_id=job_id, issue_number=issue_number)
        return JSONResponse(
            status_code=202,
            content={"status": "accepted", "event": "planner", "job_id": job_id},
        )

    # Builder triggers: agent:builder on opened or labeled — REQUIRES plan to exist
    # Safety net: if no plan, enqueue Planner first; Planner worker will enqueue Builder when done
    is_builder_trigger = (
        (action == "opened" and settings.TRIGGER_LABEL in labels)
        or (action == "labeled" and payload.get("label", {}).get("name") == settings.TRIGGER_LABEL)
    )
    if not is_builder_trigger:
        logger.info(
            "event_filtered",
            event_type=event_type,
            action=action,
            reason="not_plan_or_builder_trigger",
        )
        return {"status": "ignored"}

    # Check plan existence — Builder is pure executor, no plan = block or run Planner first
    plan_path = plan_path_for_issue(owner, repo_name, issue_number)
    plan = load_plan(plan_path)
    if plan is None:
        # Safety net: enqueue Planner; it will enqueue Builder when done (if agent:builder on issue)
        if planner_enabled(settings):
            if delivery_id and planner_is_duplicate(delivery_id):
                logger.info("planner_already_processed", delivery_id=delivery_id)
                return {"status": "already_processed"}
            job_id = f"planner-{issue_number}-{delivery_id or 'no-delivery'}"
            planner_job = PlannerJob(
                job_id=job_id,
                issue_number=issue_number,
                issue_url=issue.get("html_url", ""),
                repo_url=repo_url,
                owner=owner,
                repo=repo_name,
                payload=payload,
            )
            enqueued = await planner_enqueue(planner_job)
            if enqueued:
                if delivery_id:
                    planner_mark_processed(delivery_id)
                logger.info(
                    "planner_enqueued_for_builder_safety_net",
                    issue_number=issue_number,
                    job_id=job_id,
                )
                return JSONResponse(
                    status_code=202,
                    content={"status": "accepted", "event": "planner", "reason": "builder_needs_plan", "job_id": job_id},
                )
        # Planner disabled or enqueue failed — block Builder with comment
        background_tasks.add_task(
            post_builder_blocked_comment,
            settings.GITHUB_TOKEN,
            repo_url,
            issue_number,
        )
        logger.info("builder_blocked_no_plan", issue_number=issue_number)
        return JSONResponse(
            status_code=202,
            content={"status": "ignored", "reason": "builder_blocked_no_plan"},
        )

    job_queue = request.app.state.job_queue

    # Builder has valid plan — proceed with existing flow
    if delivery_id and job_queue.is_duplicate(delivery_id):
        logger.info("duplicate_delivery", delivery_id=delivery_id)
        return {"status": "already_processed"}

    # Race avoidance: Planner worker may have already enqueued Builder for this issue
    if job_queue.has_issue_in_queue(repo_url, issue_number):
        logger.info("builder_already_queued", issue_number=issue_number)
        return {"status": "already_processed"}

    # Self-modification detection (repo_url from payload extraction above)
    is_self = is_self_modification(repo_url, settings.BOOTY_OWN_REPO_URL)

    if is_self and not settings.BOOTY_SELF_MODIFY_ENABLED:
        issue = payload["issue"]
        logger.info("self_modification_rejected", issue_number=issue["number"])
        background_tasks.add_task(
            post_self_modification_disabled_comment,
            settings.GITHUB_TOKEN,
            repo_url,
            issue["number"],
        )
        return {
            "status": "ignored",
            "reason": "self_modification_disabled",
            "issue_number": issue["number"],
        }

    # Mark delivery as processed
    if delivery_id:
        job_queue.mark_processed(delivery_id)

    # Create and enqueue job
    issue = payload["issue"]
    job_id = f"{issue['number']}-{delivery_id}"
    job = Job(
        job_id=job_id,
        issue_url=issue["html_url"],
        issue_number=issue["number"],
        payload=payload,
        is_self_modification=is_self,
        repo_url=repo_url,
    )

    enqueued = await job_queue.enqueue(job)
    if not enqueued:
        logger.error("enqueue_failed", job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to enqueue job")

    logger.info("job_accepted", job_id=job_id, issue_number=issue["number"])
    return JSONResponse(
        status_code=202, content={"status": "accepted", "job_id": job_id}
    )


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
    booty_config = _load_booty_config_for_repo(
        settings.TARGET_REPO_URL, settings.GITHUB_TOKEN
    )
    mem_config = get_memory_config(booty_config) if booty_config else None
    if mem_config:
        mem_config = apply_memory_env_overrides(mem_config)
    if mem_config and mem_config.enabled and mem_config.comment_on_incident_issue:
        related_history = build_related_history_for_incident(
            event,
            _repo_from_url(settings.TARGET_REPO_URL),
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
        booty_config = _load_booty_config_for_repo(
            settings.TARGET_REPO_URL, settings.GITHUB_TOKEN
        )
        mem_config = get_memory_config(booty_config) if booty_config else None
        if mem_config:
            mem_config = apply_memory_env_overrides(mem_config)
        if mem_config and mem_config.enabled:
            try:
                repo = _repo_from_url(settings.TARGET_REPO_URL)
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
