"""Tests for GitHub Checks API helpers."""

from unittest.mock import MagicMock, patch

import pytest

from booty.github.checks import create_reviewer_check_run


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
