"""Tests for GitHub Checks API helpers."""

from unittest.mock import MagicMock, patch

import pytest

from booty.github.checks import create_reviewer_check_run, reviewer_check_success


def test_create_reviewer_check_run_returns_none_when_app_disabled() -> None:
    """create_reviewer_check_run returns None when get_verifier_repo returns None."""
    settings = MagicMock()
    settings.GITHUB_APP_ID = ""
    settings.GITHUB_APP_PRIVATE_KEY = ""

    with patch(
        "booty.github.checks.get_verifier_repo",
        return_value=None,
    ):
        result = create_reviewer_check_run(
            owner="owner",
            repo_name="repo",
            head_sha="abc123",
            installation_id=12345,
            settings=settings,
        )
    assert result is None


def test_create_reviewer_check_run_calls_repo_create_check_run() -> None:
    """create_reviewer_check_run calls repo.create_check_run with booty/reviewer."""
    mock_check_run = MagicMock()
    mock_repo = MagicMock()
    mock_repo.create_check_run.return_value = mock_check_run

    settings = MagicMock()

    with patch(
        "booty.github.checks.get_verifier_repo",
        return_value=mock_repo,
    ):
        result = create_reviewer_check_run(
            owner="owner",
            repo_name="repo",
            head_sha="abc123",
            installation_id=12345,
            settings=settings,
        )

    assert result is mock_check_run
    mock_repo.create_check_run.assert_called_once()
    call_kwargs = mock_repo.create_check_run.call_args[1]
    assert call_kwargs["name"] == "booty/reviewer"
    assert call_kwargs["head_sha"] == "abc123"
    assert call_kwargs["status"] == "queued"
    assert call_kwargs["output"]["title"] == "Booty Reviewer"
    assert "Queued for review" in call_kwargs["output"]["summary"]


def test_reviewer_check_success_true() -> None:
    """reviewer_check_success returns True when booty/reviewer is completed with conclusion success."""
    mock_repo = MagicMock()
    mock_commit = MagicMock()
    mock_run = MagicMock(status="completed", conclusion="success")
    mock_commit.get_check_runs.return_value = [mock_run]
    mock_repo.get_commit.return_value = mock_commit

    result = reviewer_check_success(mock_repo, "abc123")
    assert result is True
    mock_repo.get_commit.assert_called_once_with("abc123")
    mock_commit.get_check_runs.assert_called_once_with(check_name="booty/reviewer")


def test_reviewer_check_success_false_no_runs() -> None:
    """reviewer_check_success returns False when get_check_runs returns empty."""
    mock_repo = MagicMock()
    mock_commit = MagicMock()
    mock_commit.get_check_runs.return_value = []
    mock_repo.get_commit.return_value = mock_commit

    result = reviewer_check_success(mock_repo, "abc123")
    assert result is False


def test_reviewer_check_success_false_not_completed() -> None:
    """reviewer_check_success returns False when run has status in_progress."""
    mock_repo = MagicMock()
    mock_commit = MagicMock()
    mock_run = MagicMock(status="in_progress", conclusion=None)
    mock_commit.get_check_runs.return_value = [mock_run]
    mock_repo.get_commit.return_value = mock_commit

    result = reviewer_check_success(mock_repo, "abc123")
    assert result is False


def test_reviewer_check_success_false_failure() -> None:
    """reviewer_check_success returns False when run has conclusion failure."""
    mock_repo = MagicMock()
    mock_commit = MagicMock()
    mock_run = MagicMock(status="completed", conclusion="failure")
    mock_commit.get_check_runs.return_value = [mock_run]
    mock_repo.get_commit.return_value = mock_commit

    result = reviewer_check_success(mock_repo, "abc123")
    assert result is False


def test_reviewer_check_success_exception() -> None:
    """reviewer_check_success returns False when get_commit or get_check_runs raises (fail closed)."""
    mock_repo = MagicMock()
    mock_repo.get_commit.side_effect = Exception("API error")

    result = reviewer_check_success(mock_repo, "abc123")
    assert result is False
