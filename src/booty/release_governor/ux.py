"""Release Governor operator UX — commit status for HOLD/ALLOW (GOV-15, GOV-23, GOV-24, GOV-25)."""

from booty.release_governor.decision import Decision


def post_hold_status(
    gh_repo, head_sha: str, decision: Decision, target_url: str, approval_hint: str | None = None
) -> None:
    """Post HOLD commit status (GOV-15, GOV-23).

    context='booty/release-governor', state='failure'.
    Description: HOLD: {reason} — {sha[:7]}. Max 140 chars.
    approval_hint: e.g. 'Approval via label: release:approved' for high_risk_no_approval.
    """
    sha_short = head_sha[:7] if head_sha else "?"
    reason = decision.reason

    # Reason-specific "how to unblock" summary (max 140 chars total)
    unblock_map = {
        "deploy_not_configured": "Configure deploy_workflow_name in .booty.yml",
        "first_deploy_required": f"First deploy for {sha_short} — add approval then retry",
        "degraded_high_risk": "Resolve incident; or wait for recovery",
        "degraded_medium_hold": "Resolve incident; or wait for recovery",
        "cooldown": "Wait for cooldown before retry",
        "rate_limit": "Max deploys/hour reached — wait before retry",
        "high_risk_no_approval": approval_hint or "HIGH risk — approval required (see target URL)",
    }
    unblock = unblock_map.get(reason, f"HOLD: {reason}")
    desc = f"HOLD: {unblock} — {sha_short}"
    if len(desc) > 140:
        desc = desc[:137] + "..."

    commit = gh_repo.get_commit(head_sha)
    commit.create_status(
        state="failure",
        target_url=target_url or "",
        description=desc,
        context="booty/release-governor",
    )


def post_allow_status(gh_repo, head_sha: str, target_url: str) -> None:
    """Post ALLOW commit status (GOV-24).

    context='booty/release-governor', state='success'.
    Description: "Triggered: deploy workflow run" or similar.
    """
    commit = gh_repo.get_commit(head_sha)
    commit.create_status(
        state="success",
        target_url=target_url or "",
        description="Triggered: deploy workflow run",
        context="booty/release-governor",
    )
