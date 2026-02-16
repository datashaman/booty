"""Tests for Release Governor workflow_run handler."""

import unittest.mock

import pytest

from booty.release_governor.decision import Decision
from booty.release_governor.handler import handle_workflow_run
from booty.test_runner.config import ReleaseGovernorConfig


@pytest.fixture
def minimal_payload():
    return {
        "workflow_run": {
            "head_sha": "abc123def456",
            "head_branch": "main",
            "name": "Verify main",
        },
        "repository": {"full_name": "owner/repo"},
    }


@pytest.fixture
def mock_config():
    return ReleaseGovernorConfig(
        verification_workflow_name="Verify main",
        deploy_workflow_name="deploy.yml",
        max_deploys_per_hour=6,
    )


def test_handle_workflow_run_returns_decision(minimal_payload, mock_config):
    """Handler returns Decision with outcome in (ALLOW, HOLD)."""
    mock_compare = unittest.mock.MagicMock()
    mock_compare.files = []  # Empty diff -> LOW risk

    with unittest.mock.patch("booty.release_governor.handler.Github") as MockGithub:
        mock_repo = unittest.mock.MagicMock()
        mock_repo.compare.return_value = mock_compare
        MockGithub.return_value.get_repo.return_value = mock_repo

        with unittest.mock.patch(
            "booty.release_governor.handler.get_settings"
        ) as mock_settings:
            mock_settings.return_value.GITHUB_TOKEN = "token"

            with unittest.mock.patch(
                "booty.release_governor.handler.get_state_dir"
            ) as mock_state_dir:
                import tempfile
                from pathlib import Path
                with tempfile.TemporaryDirectory() as d:
                    mock_state_dir.return_value = Path(d)
                    decision = handle_workflow_run(minimal_payload, mock_config)

    assert isinstance(decision, Decision)
    assert decision.outcome in ("ALLOW", "HOLD")
    assert decision.sha == "abc123def456"
    assert decision.risk_class in ("LOW", "MEDIUM", "HIGH")


def test_uses_head_sha_from_payload(minimal_payload, mock_config):
    """Handler uses workflow_run.head_sha from payload, not latest main."""
    mock_compare = unittest.mock.MagicMock()
    mock_compare.files = []

    mock_settings = unittest.mock.MagicMock()
    mock_settings.GITHUB_TOKEN = "token"

    with unittest.mock.patch("booty.release_governor.handler.Github") as MockGithub:
        mock_repo = unittest.mock.MagicMock()
        mock_repo.compare.return_value = mock_compare
        MockGithub.return_value.get_repo.return_value = mock_repo

        with unittest.mock.patch(
            "booty.release_governor.handler.get_settings",
            return_value=mock_settings,
        ):
            with unittest.mock.patch(
                "booty.release_governor.handler.get_state_dir"
            ) as mock_state_dir:
                import tempfile
                from pathlib import Path
                with tempfile.TemporaryDirectory() as d:
                    mock_state_dir.return_value = Path(d)
                    decision = handle_workflow_run(minimal_payload, mock_config)

    assert decision.sha == "abc123def456"
    mock_repo.compare.assert_called_once()
    call_args = mock_repo.compare.call_args[0]
    assert call_args[1] == "abc123def456"  # head=second arg to compare(base, head)
