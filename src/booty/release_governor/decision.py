"""Decision engine: ALLOW or HOLD based on risk, approval, cooldown, rate limit (GOV-08 to GOV-13)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from booty.release_governor.store import (
    ReleaseState,
    get_deploys_in_last_hour,
    load_release_state,
)
from booty.test_runner.config import ReleaseGovernorConfig


@dataclass
class Decision:
    """Governor decision outcome."""

    outcome: Literal["ALLOW", "HOLD"]
    reason: str
    risk_class: str
    sha: str


def compute_decision(
    head_sha: str,
    risk_class: Literal["LOW", "MEDIUM", "HIGH"],
    config: ReleaseGovernorConfig,
    state: ReleaseState,
    state_dir: Path,
    degraded: bool | None,
    approval_context: dict,
    is_first_deploy: bool,
) -> Decision:
    """Compute ALLOW or HOLD based on rules (GOV-08 to GOV-13)."""
    now = datetime.now(timezone.utc)

    # Hard holds
    if not config.deploy_workflow_name or not config.deploy_workflow_name.strip():
        return Decision("HOLD", "deploy_not_configured", risk_class, head_sha)

    if (
        is_first_deploy
        and config.require_approval_for_first_deploy
        and not any(approval_context.get(k, False) for k in ("env_approved", "label_approved", "comment_approved"))
    ):
        return Decision("HOLD", "first_deploy_required", risk_class, head_sha)

    if degraded is True and risk_class == "HIGH":
        return Decision("HOLD", "degraded_high_risk", risk_class, head_sha)

    # Cooldown (GOV-12)
    if (
        state.last_deploy_attempt_sha == head_sha
        and state.last_deploy_result == "failure"
        and state.last_deploy_time
    ):
        try:
            last_dt = datetime.fromisoformat(state.last_deploy_time.replace("Z", "+00:00"))
            delta_min = (now - last_dt).total_seconds() / 60
            if delta_min < config.cooldown_minutes:
                return Decision("HOLD", "cooldown", risk_class, head_sha)
        except (ValueError, TypeError):
            pass

    # Rate limit (GOV-13)
    if get_deploys_in_last_hour(state_dir) >= config.max_deploys_per_hour:
        return Decision("HOLD", "rate_limit", risk_class, head_sha)

    # Risk-based rules
    if risk_class == "LOW":
        return Decision("ALLOW", "allow_low", risk_class, head_sha)

    if risk_class == "MEDIUM":
        if degraded is True:
            return Decision("HOLD", "degraded_medium_hold", risk_class, head_sha)
        return Decision("ALLOW", "allow_medium", risk_class, head_sha)

    # HIGH
    if any(approval_context.get(k, False) for k in ("env_approved", "label_approved", "comment_approved")):
        return Decision("ALLOW", "allow_high_approved", risk_class, head_sha)
    return Decision("HOLD", "high_risk_no_approval", risk_class, head_sha)
