"""Release Governor handler — workflow_run pipeline (GOV-01, GOV-02, GOV-03)."""

import os
from typing import Literal

from github import Github

from booty.config import get_settings
from booty.release_governor.decision import Decision, compute_decision
from booty.release_governor.risk import compute_risk_class
from booty.release_governor.store import get_state_dir, load_release_state
from booty.test_runner.config import ReleaseGovernorConfig


def handle_workflow_run(
    payload: dict, config: ReleaseGovernorConfig
) -> Decision:
    """Handle workflow_run webhook: compute risk and decision.

    Args:
        payload: GitHub workflow_run webhook payload
        config: ReleaseGovernorConfig (from repo .booty.yml, env overrides applied)

    Returns:
        Decision with outcome (ALLOW/HOLD), reason, risk_class, sha
    """
    wr = payload.get("workflow_run", {})
    head_sha = wr.get("head_sha", "")
    repo_info = payload.get("repository", {})
    repo_full_name = repo_info.get("full_name", "")

    state_dir = get_state_dir()
    state = load_release_state(state_dir)

    production_sha = (
        state.production_sha_current
        or state.production_sha_previous
        or head_sha
    )

    gh = Github(get_settings().GITHUB_TOKEN)
    gh_repo = gh.get_repo(repo_full_name)
    comparison = gh_repo.compare(production_sha, head_sha)

    risk_class: Literal["LOW", "MEDIUM", "HIGH"] = compute_risk_class(
        comparison, config
    )

    degraded: bool | None = None  # Stub; future Sentry integration

    env_approved = (
        os.environ.get("RELEASE_GOVERNOR_APPROVED", "").lower()
        in ("1", "true", "yes")
    )
    approval_context = {
        "env_approved": env_approved,
        "label_approved": False,  # TODO: Phase 16 — PR label check
        "comment_approved": False,  # TODO: Phase 16 — PR comment check
    }

    is_first_deploy = state.production_sha_current is None

    decision = compute_decision(
        head_sha=head_sha,
        risk_class=risk_class,
        config=config,
        state=state,
        state_dir=state_dir,
        degraded=degraded,
        approval_context=approval_context,
        is_first_deploy=is_first_deploy,
    )

    return decision
