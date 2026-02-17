"""Structured skip logging for router (OPS-01, OPS-02)."""

from booty.logging import get_logger

logger = get_logger()

# Map granular router reasons to five OPS-02 buckets
REASON_TO_BUCKET = {
    "normalize_failed": "normalize_failed",
    "unsupported_event": "not_agent_pr",
    "not_plan_or_builder_trigger": "not_agent_pr",
    "unhandled_action": "not_agent_pr",
    "workflow_not_completed": "not_agent_pr",
    "workflow_not_matched": "not_agent_pr",
    "no_trigger_label": "not_agent_pr",
    "all_pr_agents_disabled": "disabled",
    "governor_disabled": "disabled",
    "builder_blocked_no_plan": "not_agent_pr",
    "no_job_queue": "missing_config",
    "self_modification_disabled": "disabled",
    "verifier_already_processed": "dedup_hit",
    "dedup_hit": "dedup_hit",
    "missing_head_sha": "normalize_failed",
}

# Operator-actionable skips: INFO
INFO_BUCKETS = frozenset({"disabled", "missing_config", "normalize_failed"})


def _log_event_skip(
    agent: str | None,
    repo: str | None,
    event_type: str,
    reason: str,
    *,
    _reason_raw: str | None = None,
) -> None:
    """Log router event skip with five-bucket vocabulary and INFO/DEBUG split."""
    bucket = REASON_TO_BUCKET.get(reason, "not_agent_pr")
    raw = _reason_raw or reason
    log_fn = logger.info if bucket in INFO_BUCKETS else logger.debug
    log_fn(
        "event_skip",
        agent=agent,
        repo=repo,
        event_type=event_type,
        decision="skip",
        reason=bucket,
        _reason_raw=raw,
    )
