"""GitHub webhook handler with HMAC verification."""

import hmac
import hashlib
import re

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse

from booty.config import get_settings, verifier_enabled
from booty.github.comments import post_self_modification_disabled_comment
from booty.jobs import Job
from booty.logging import get_logger
from booty.self_modification.detector import is_self_modification
from booty.verifier import VerifierJob


router = APIRouter(prefix="/webhooks")


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

    # Handle pull_request events (Verifier)
    if event_type == "pull_request":
        verifier_queue = getattr(request.app.state, "verifier_queue", None)
        if verifier_queue is None or not verifier_enabled(settings):
            logger.info(
                "event_filtered",
                event_type=event_type,
                reason="verifier_disabled",
            )
            return {"status": "ignored", "reason": "verifier_disabled"}

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
        )

        if not head_sha:
            logger.warning("pull_request_missing_head_sha", pr_number=pr_number)
            return {"status": "ignored", "reason": "missing_head_sha"}

        if verifier_queue.is_duplicate(pr_number, head_sha):
            logger.info(
                "verifier_already_processed",
                pr_number=pr_number,
                head_sha=head_sha[:7],
            )
            return {"status": "already_processed"}

        # Extract issue number from branch name (agent/issue-N)
        issue_number_from_branch = None
        branch_match = re.match(r"^agent/issue-(\d+)$", head_ref)
        if branch_match:
            issue_number_from_branch = int(branch_match.group(1))

        job_id = f"verifier-{pr_number}-{head_sha[:7]}"
        job = VerifierJob(
            job_id=job_id,
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
        if not enqueued:
            logger.error("verifier_enqueue_failed", job_id=job_id)
            raise HTTPException(status_code=500, detail="Failed to enqueue verifier job")

        logger.info("verifier_job_accepted", job_id=job_id, pr_number=pr_number)
        return JSONResponse(
            status_code=202,
            content={"status": "accepted", "job_id": job_id},
        )

    # Handle issues events (Builder)
    if event_type != "issues":
        logger.info("event_filtered", event_type=event_type, reason="not_issues")
        return {"status": "ignored"}

    job_queue = request.app.state.job_queue

    # Check idempotency
    if delivery_id and job_queue.is_duplicate(delivery_id):
        logger.info("duplicate_delivery", delivery_id=delivery_id)
        return {"status": "already_processed"}

    if payload.get("action") != "labeled":
        logger.info(
            "event_filtered",
            event_type=event_type,
            action=payload.get("action"),
            reason="not_labeled",
        )
        return {"status": "ignored"}

    if payload.get("label", {}).get("name") != settings.TRIGGER_LABEL:
        logger.info(
            "event_filtered",
            label=payload.get("label", {}).get("name"),
            trigger_label=settings.TRIGGER_LABEL,
            reason="wrong_label",
        )
        return {"status": "ignored"}

    # Self-modification detection
    repo_url = payload.get("repository", {}).get("html_url", "")
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
