"""Tests for GitHub comment helpers."""

from unittest.mock import MagicMock, patch

import pytest

from booty.github.comments import (
    get_plan_comment_body,
    update_plan_comment_with_architect_section_if_changed,
)


def test_get_plan_comment_body_found() -> None:
    """get_plan_comment_body returns body when comment contains <!-- booty-plan -->."""
    body = "Plan body\n\n<!-- booty-plan -->\ncontent"
    mock_comment = MagicMock()
    mock_comment.body = body
    mock_issue = MagicMock()
    mock_issue.get_comments.return_value = [mock_comment]
    mock_repo = MagicMock()
    mock_repo.get_issue.return_value = mock_issue

    with patch("booty.github.comments._get_repo", return_value=mock_repo):
        result = get_plan_comment_body("token", "https://github.com/owner/repo", 1)
    assert result == body


def test_get_plan_comment_body_not_found() -> None:
    """get_plan_comment_body returns None when no plan comment exists."""
    mock_comment = MagicMock()
    mock_comment.body = "Some other comment without booty-plan"
    mock_issue = MagicMock()
    mock_issue.get_comments.return_value = [mock_comment]
    mock_repo = MagicMock()
    mock_repo.get_issue.return_value = mock_issue

    with patch("booty.github.comments._get_repo", return_value=mock_repo):
        result = get_plan_comment_body("token", "https://github.com/owner/repo", 1)
    assert result is None


def test_update_if_changed_skips_when_identical() -> None:
    """update_plan_comment_with_architect_section_if_changed returns False when blocks identical."""
    architect_section = "<!-- booty-architect -->\n✓ Approved\n<!-- /booty-architect -->"
    body = f"Plan\n\n{architect_section}\n\n<details>more</details>\n<!-- booty-plan -->"
    mock_comment = MagicMock()
    mock_comment.body = body
    mock_issue = MagicMock()
    mock_issue.get_comments.return_value = [mock_comment]
    mock_repo = MagicMock()
    mock_repo.get_issue.return_value = mock_issue

    with (
        patch("booty.github.comments._get_repo", return_value=mock_repo),
        patch(
            "booty.github.comments.update_plan_comment_with_architect_section"
        ) as mock_update,
    ):
        result = update_plan_comment_with_architect_section_if_changed(
            "token", "https://github.com/owner/repo", 1, architect_section
        )
    assert result is False
    mock_update.assert_not_called()


def test_update_if_changed_calls_when_different() -> None:
    """update_plan_comment_with_architect_section_if_changed calls update when block differs."""
    new_section = "<!-- booty-architect -->\n✓ Approved\n<!-- /booty-architect -->"
    old_section = "<!-- booty-architect -->\nBlocked\n<!-- /booty-architect -->"
    body = f"Plan\n\n{old_section}\n\n<details>more</details>\n<!-- booty-plan -->"
    mock_comment = MagicMock()
    mock_comment.body = body
    mock_issue = MagicMock()
    mock_issue.get_comments.return_value = [mock_comment]
    mock_repo = MagicMock()
    mock_repo.get_issue.return_value = mock_issue

    with (
        patch("booty.github.comments._get_repo", return_value=mock_repo),
        patch(
            "booty.github.comments.update_plan_comment_with_architect_section"
        ) as mock_update,
    ):
        result = update_plan_comment_with_architect_section_if_changed(
            "token", "https://github.com/owner/repo", 1, new_section
        )
    assert result is True
    mock_update.assert_called_once_with(
        "token", "https://github.com/owner/repo", 1, new_section
    )
