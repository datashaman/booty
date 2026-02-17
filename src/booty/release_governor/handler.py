"""Release Governor handler — workflow_run pipeline (GOV-01, GOV-02, GOV-03)."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from github import Github

from booty.config import get_settings
from booty.logging import get_logger
from booty.release_governor.decision import Decision, compute_decision
from booty.release_governor.deploy import dispatch_deploy
from booty.release_governor.override import get_security_override_with_poll
from booty.release_governor.risk import compute_risk_class, get_risk_paths
from booty.release_governor.store import (
    append_deploy_to_history,
    get_state_dir,
    load_release_state,
    record_delivery_id,
    save_release_state,
)
from booty.release_governor.ux import post_allow_status, post_hold_status
from booty.test_runner.config import ReleaseGovernorConfig

if TYPE_CHECKING:
    from booty.test_runner.config import BootyConfig


def simulate_decision_for_cli(
    repo: str,
    head_sha: str,
    config: ReleaseGovernorConfig,
    workspace: Path,
    state_dir_override: Path | None = None,
) -> tuple[Decision, list[str]]:
    """Compute decision for CLI simulate/trigger without webhook payload.

    Args:
        repo: owner/repo
        head_sha: commit SHA to evaluate
        config: effective ReleaseGovernorConfig
        workspace: workspace path (for state dir when override not set)
        state_dir_override: optional state dir override (e.g. workspace/.booty/state)

    Returns:
        (Decision, risk_paths) — risk_paths from get_risk_paths when --show-paths
    """
    state_dir = state_dir_override or get_state_dir()
    state = load_release_state(state_dir)

    production_sha = (
        state.production_sha_current
        or state.production_sha_previous
        or head_sha
    )

    token = get_settings().GITHUB_TOKEN
    if not token or not token.strip():
        raise ValueError("GITHUB_TOKEN required for simulate; set it to fetch diff")

    gh = Github(token)
    gh_repo = gh.get_repo(repo)
    comparison = gh_repo.compare(production_sha, head_sha)

    # CLI: no polling — single check. Webhook uses poll for Security race.
    override = get_security_override_with_poll(
        state_dir, repo, head_sha, max_wait_sec=0
    )
    if override is not None:
        risk_class = "HIGH"
    else:
        risk_class = compute_risk_class(comparison, config)
    risk_paths = get_risk_paths(comparison, config)

    degraded: bool | None = None

    raw_val = (
        os.environ.get("RELEASE_GOVERNOR_APPROVED", "")
        .split("#")[0]  # drop inline comment (systemd may pass it through)
        .strip()
        .strip('"\'')
        .lower()
    )
    env_approved = raw_val in ("1", "true", "yes")
    approval_context = {
        "env_approved": env_approved,
        "label_approved": False,
        "comment_approved": False,
    }

    is_first_deploy = state.production_sha_current is None

    # Diagnostic: log approval context when HIGH risk to debug HOLD vs ALLOW
    if risk_class == "HIGH":
        get_logger().info(
            "governor_approval_context",
            repo=repo,
            head_sha=head_sha[:7],
            risk_class=risk_class,
            env_approved=env_approved,
        )

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

    return decision, risk_paths


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

    override = get_security_override_with_poll(state_dir, repo_full_name, head_sha)
    if override is not None:
        risk_class = "HIGH"
    else:
        risk_class = compute_risk_class(comparison, config)

    degraded: bool | None = None  # Stub; future Sentry integration

    raw_val = (
        os.environ.get("RELEASE_GOVERNOR_APPROVED", "")
        .split("#")[0]  # drop inline comment (systemd may pass it through)
        .strip()
        .strip('"\'')
        .lower()
    )
    env_approved = raw_val in ("1", "true", "yes")
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


def apply_governor_decision(
    gh_repo,
    head_sha: str,
    decision: Decision,
    governor_config: ReleaseGovernorConfig,
    repo_full_name: str,
    html_url: str,
    delivery_id: str | None,
    state_dir,
    booty_config: "BootyConfig | None" = None,
    surface_hold_fn=None,
) -> None:
    """Apply Governor decision: dispatch deploy or post HOLD, update state, record delivery.

    Shared by workflow_run verification path and main verification path.
    """
    default_branch = getattr(gh_repo, "default_branch", None) or "main"
    actions_url = f"{html_url.rstrip('/')}/actions" if html_url else ""
    hold_docs_url = (
        f"{html_url.rstrip('/')}/blob/{default_branch}/docs/release-governor.md"
        if html_url else ""
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
        if surface_hold_fn:
            surface_hold_fn()
        if booty_config:
            from booty.memory import add_record, get_memory_config
            from booty.memory.adapters import build_governor_hold_record
            from booty.memory.config import apply_memory_env_overrides

            mem_config = get_memory_config(booty_config)
            if mem_config:
                mem_config = apply_memory_env_overrides(mem_config)
            if mem_config and mem_config.enabled:
                try:
                    record = build_governor_hold_record(decision, repo_full_name)
                    add_record(record, mem_config)
                except Exception:
                    from booty.logging import get_logger
                    get_logger().warning(
                        "memory_ingestion_failed",
                        type="governor_hold",
                        error="add_record failed",
                    )

    if delivery_id:
        record_delivery_id(state_dir, repo_full_name, head_sha, delivery_id)
