"""GitHub webhook handler with HMAC verification."""

import hmac
import hashlib

from fastapi import APIRouter, HTTPException, Request

from booty.config import get_settings
from booty.jobs import Job
from booty.logging import get_logger


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
async def github_webhook(request: Request):
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

    # Get job queue from app state
    job_queue = request.app.state.job_queue

    # Check idempotency
    if delivery_id and job_queue.is_duplicate(delivery_id):
        logger.info("duplicate_delivery", delivery_id=delivery_id)
        return {"status": "already_processed"}

    # Parse payload
    payload = await request.json()

    # Filter: only process issues labeled events with trigger label
    if event_type != "issues":
        logger.info("event_filtered", event_type=event_type, reason="not_issues")
        return {"status": "ignored"}

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
    )

    enqueued = await job_queue.enqueue(job)
    if not enqueued:
        logger.error("enqueue_failed", job_id=job_id)
        raise HTTPException(status_code=500, detail="Failed to enqueue job")

    logger.info("job_accepted", job_id=job_id, issue_number=issue["number"])
    return {"status": "accepted", "job_id": job_id}
