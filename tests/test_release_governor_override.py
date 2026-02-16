"""Tests for Release Governor Security override consumption."""

import json
import time
from datetime import datetime, timezone, timedelta

import pytest

from booty.release_governor.override import (
    get_security_override,
    get_security_override_with_poll,
)
from booty.release_governor.store import get_state_dir


@pytest.fixture
def temp_state_dir(tmp_path, monkeypatch):
    """Use temp dir for state."""
    monkeypatch.setenv("RELEASE_GOVERNOR_STATE_DIR", str(tmp_path))
    yield get_state_dir()


def test_get_security_override_returns_none_when_file_missing(
    temp_state_dir,
) -> None:
    """get_security_override returns None when file missing."""
    assert get_security_override(temp_state_dir, "owner/repo", "abc123") is None


def test_get_security_override_returns_none_when_key_missing(
    temp_state_dir,
) -> None:
    """get_security_override returns None when key does not exist."""
    path = temp_state_dir / "security_overrides.json"
    path.write_text(json.dumps({"other/repo:xyz": {"risk_override": "HIGH"}}))
    assert get_security_override(temp_state_dir, "owner/repo", "abc123") is None


def test_get_security_override_returns_entry_when_exists(temp_state_dir) -> None:
    """get_security_override returns entry when key exists."""
    path = temp_state_dir / "security_overrides.json"
    entry = {
        "risk_override": "HIGH",
        "reason": "permission_surface_change",
        "sha": "abc123",
        "paths": [".github/workflows/ci.yml"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps({"owner/repo:abc123": entry}))
    result = get_security_override(temp_state_dir, "owner/repo", "abc123")
    assert result is not None
    assert result["risk_override"] == "HIGH"
    assert result["paths"] == [".github/workflows/ci.yml"]


def test_get_security_override_prunes_expired(temp_state_dir) -> None:
    """get_security_override prunes entries older than 14 days."""
    path = temp_state_dir / "security_overrides.json"
    old_date = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
    data = {
        "owner/repo:expired": {
            "risk_override": "HIGH",
            "reason": "permission_surface_change",
            "sha": "expired",
            "paths": ["x"],
            "created_at": old_date,
        },
        "owner/repo:valid": {
            "risk_override": "HIGH",
            "reason": "permission_surface_change",
            "sha": "valid",
            "paths": ["y"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    path.write_text(json.dumps(data))
    result = get_security_override(temp_state_dir, "owner/repo", "valid")
    assert result is not None
    assert result["sha"] == "valid"
    # Expired should be pruned from file
    with open(path) as f:
        updated = json.load(f)
    assert "owner/repo:expired" not in updated
    assert "owner/repo:valid" in updated


def test_get_security_override_with_poll_returns_immediately(temp_state_dir) -> None:
    """get_security_override_with_poll returns immediately when override present."""
    from booty.security.override import persist_override

    persist_override("owner/repo", "abc123", [".github/workflows/ci.yml"])
    start = time.monotonic()
    result = get_security_override_with_poll(
        temp_state_dir, "owner/repo", "abc123", max_wait_sec=2, interval_sec=1.0
    )
    elapsed = time.monotonic() - start
    assert result is not None
    assert result["risk_override"] == "HIGH"
    assert elapsed < 1.0


def test_get_security_override_with_poll_returns_none_after_timeout(
    temp_state_dir,
) -> None:
    """get_security_override_with_poll returns None after timeout when absent."""
    start = time.monotonic()
    result = get_security_override_with_poll(
        temp_state_dir, "owner/repo", "nonexistent", max_wait_sec=1, interval_sec=0.2
    )
    elapsed = time.monotonic() - start
    assert result is None
    assert elapsed >= 0.9


def test_handle_workflow_run_uses_high_when_override_present(
    temp_state_dir,
) -> None:
    """handle_workflow_run uses risk_class HIGH when Security override present."""
    import unittest.mock

    from booty.release_governor.handler import handle_workflow_run
    from booty.security.override import persist_override
    from booty.test_runner.config import ReleaseGovernorConfig

    persist_override("owner/repo", "abc123def456", [".github/workflows/x.yml"])

    mock_compare = unittest.mock.MagicMock()
    mock_compare.files = []  # Empty diff -> would be LOW without override

    with unittest.mock.patch("booty.release_governor.handler.Github") as MockGithub:
        mock_repo = unittest.mock.MagicMock()
        mock_repo.compare.return_value = mock_compare
        MockGithub.return_value.get_repo.return_value = mock_repo

        with unittest.mock.patch(
            "booty.release_governor.handler.get_settings"
        ) as mock_settings:
            mock_settings.return_value.GITHUB_TOKEN = "token"

            with unittest.mock.patch(
                "booty.release_governor.handler.get_state_dir",
                return_value=temp_state_dir,
            ):
                payload = {
                    "workflow_run": {"head_sha": "abc123def456"},
                    "repository": {"full_name": "owner/repo"},
                }
                config = ReleaseGovernorConfig(
                    verification_workflow_name="Verify main",
                    deploy_workflow_name="deploy.yml",
                    max_deploys_per_hour=6,
                )
                decision = handle_workflow_run(payload, config)

    assert decision.risk_class == "HIGH"
