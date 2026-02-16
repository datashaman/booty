"""Tests for decision engine (GOV-08 to GOV-13)."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from booty.release_governor.decision import Decision, compute_decision
from booty.release_governor.store import (
    ReleaseState,
    append_deploy_to_history,
    load_release_state,
)
from booty.test_runner.config import ReleaseGovernorConfig


def _empty_state() -> ReleaseState:
    return ReleaseState()


def _config(
    deploy_workflow_name: str = "deploy.yml",
    require_approval_for_first_deploy: bool = False,
    cooldown_minutes: int = 30,
    max_deploys_per_hour: int = 6,
) -> ReleaseGovernorConfig:
    return ReleaseGovernorConfig(
        deploy_workflow_name=deploy_workflow_name,
        require_approval_for_first_deploy=require_approval_for_first_deploy,
        cooldown_minutes=cooldown_minutes,
        max_deploys_per_hour=max_deploys_per_hour,
    )


def test_low_risk_allow():
    config = _config()
    state = _empty_state()
    with tempfile.TemporaryDirectory() as d:
        state_dir = Path(d)
        decision = compute_decision(
            "abc123",
            "LOW",
            config,
            state,
            state_dir,
            degraded=None,
            approval_context={},
            is_first_deploy=True,
        )
    assert decision.outcome == "ALLOW"
    assert decision.reason == "allow_low"


def test_medium_no_incident_allow():
    config = _config()
    state = _empty_state()
    with tempfile.TemporaryDirectory() as d:
        decision = compute_decision(
            "abc123",
            "MEDIUM",
            config,
            state,
            Path(d),
            degraded=False,
            approval_context={},
            is_first_deploy=False,
        )
    assert decision.outcome == "ALLOW"
    assert decision.reason == "allow_medium"


def test_medium_degraded_hold():
    config = _config()
    state = _empty_state()
    with tempfile.TemporaryDirectory() as d:
        decision = compute_decision(
            "abc123",
            "MEDIUM",
            config,
            state,
            Path(d),
            degraded=True,
            approval_context={},
            is_first_deploy=False,
        )
    assert decision.outcome == "HOLD"
    assert "degraded" in decision.reason


def test_high_no_approval_hold():
    config = _config()
    state = _empty_state()
    with tempfile.TemporaryDirectory() as d:
        decision = compute_decision(
            "abc123",
            "HIGH",
            config,
            state,
            Path(d),
            degraded=None,
            approval_context={"env_approved": False, "label_approved": False, "comment_approved": False},
            is_first_deploy=False,
        )
    assert decision.outcome == "HOLD"
    assert decision.reason == "high_risk_no_approval"


def test_high_env_approval_allow():
    config = _config()
    state = _empty_state()
    with tempfile.TemporaryDirectory() as d:
        decision = compute_decision(
            "abc123",
            "HIGH",
            config,
            state,
            Path(d),
            degraded=None,
            approval_context={"env_approved": True, "label_approved": False, "comment_approved": False},
            is_first_deploy=False,
        )
    assert decision.outcome == "ALLOW"
    assert decision.reason == "allow_high_approved"


def test_cooldown_hold():
    config = _config(cooldown_minutes=60)
    now = datetime.now(timezone.utc)
    state = ReleaseState(
        last_deploy_attempt_sha="abc123",
        last_deploy_time=now.isoformat(),
        last_deploy_result="failure",
    )
    with tempfile.TemporaryDirectory() as d:
        decision = compute_decision(
            "abc123",
            "LOW",
            config,
            state,
            Path(d),
            degraded=None,
            approval_context={},
            is_first_deploy=False,
        )
    assert decision.outcome == "HOLD"
    assert decision.reason == "cooldown"


def test_rate_limit_hold():
    config = _config(max_deploys_per_hour=2)
    state = _empty_state()
    with tempfile.TemporaryDirectory() as d:
        state_dir = Path(d)
        now = datetime.now(timezone.utc).isoformat()
        for _ in range(3):
            append_deploy_to_history(state_dir, "x", now, "success")
        decision = compute_decision(
            "abc123",
            "LOW",
            config,
            load_release_state(state_dir),
            state_dir,
            degraded=None,
            approval_context={},
            is_first_deploy=False,
        )
    assert decision.outcome == "HOLD"
    assert decision.reason == "rate_limit"


def test_first_deploy_required_hold():
    config = _config(require_approval_for_first_deploy=True)
    state = ReleaseState(production_sha_current=None)
    with tempfile.TemporaryDirectory() as d:
        decision = compute_decision(
            "abc123",
            "LOW",
            config,
            state,
            Path(d),
            degraded=None,
            approval_context={"env_approved": False, "label_approved": False, "comment_approved": False},
            is_first_deploy=True,
        )
    assert decision.outcome == "HOLD"
    assert decision.reason == "first_deploy_required"


def test_degraded_high_hold():
    config = _config()
    state = _empty_state()
    with tempfile.TemporaryDirectory() as d:
        decision = compute_decision(
            "abc123",
            "HIGH",
            config,
            state,
            Path(d),
            degraded=True,
            approval_context={"env_approved": True},
            is_first_deploy=False,
        )
    assert decision.outcome == "HOLD"
    assert decision.reason == "degraded_high_risk"


def test_deploy_not_configured_hold():
    config = _config(deploy_workflow_name="")
    state = _empty_state()
    with tempfile.TemporaryDirectory() as d:
        decision = compute_decision(
            "abc123",
            "LOW",
            config,
            state,
            Path(d),
            degraded=None,
            approval_context={},
            is_first_deploy=False,
        )
    assert decision.outcome == "HOLD"
    assert decision.reason == "deploy_not_configured"
