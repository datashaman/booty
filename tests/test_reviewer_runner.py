"""Tests for Reviewer runner — integration with engine, check conclusion, comment posting."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from booty.reviewer.engine import format_reviewer_comment
from booty.reviewer.schema import CategoryResult, ReviewResult


def _make_result(decision: str, blocking_categories: list[str] | None = None) -> ReviewResult:
    cats = [
        CategoryResult(category="Overengineering", grade="PASS", findings=[]),
        CategoryResult(category="Architectural drift", grade="PASS", findings=[]),
        CategoryResult(category="Tests", grade="PASS", findings=[]),
        CategoryResult(category="Duplication", grade="PASS", findings=[]),
        CategoryResult(category="Maintainability", grade="PASS", findings=[]),
        CategoryResult(category="Naming/API", grade="PASS", findings=[]),
    ]
    return ReviewResult(
        decision=decision,
        categories=cats,
        blocking_categories=blocking_categories or [],
    )


def test_format_reviewer_comment_produces_valid_structure() -> None:
    """format_reviewer_comment produces sections and marker."""
    result = _make_result("APPROVED")
    body = format_reviewer_comment(result)
    assert "<!-- booty-reviewer -->" in body
    assert "<!-- /booty-reviewer -->" in body
    assert "## Reviewer: APPROVED" in body
    assert "### Overengineering" in body
    assert "Status: PASS" in body


def test_format_reviewer_comment_approved_with_suggestions() -> None:
    """APPROVED_WITH_SUGGESTIONS shows decision, no Blocking line."""
    result = _make_result("APPROVED_WITH_SUGGESTIONS")
    body = format_reviewer_comment(result)
    assert "## Reviewer: APPROVED_WITH_SUGGESTIONS" in body
    assert "Blocking:" not in body


def test_format_reviewer_comment_blocked_includes_rationale() -> None:
    """When BLOCKED, body includes Blocking line."""
    result = _make_result("BLOCKED", blocking_categories=["Overengineering"])
    body = format_reviewer_comment(result)
    assert "Blocking: Overengineering" in body
    assert "## Reviewer: BLOCKED" in body


@pytest.mark.asyncio
async def test_process_reviewer_job_approved_success() -> None:
    """process_reviewer_job with APPROVED result → edit_check_run conclusion=success, title=Reviewer approved."""
    from booty.reviewer.config import ReviewerConfig
    from booty.reviewer.job import ReviewerJob
    from booty.reviewer.runner import process_reviewer_job

    job = ReviewerJob(
        job_id="r-1",
        owner="o",
        repo_name="r",
        pr_number=1,
        head_sha="abc123",
        head_ref="feat",
        repo_url="https://github.com/o/r",
        installation_id=1,
        payload={
            "pull_request": {
                "title": "PR",
                "body": "Body",
                "base": {"sha": "base123", "ref": "main"},
                "head": {"sha": "abc123", "ref": "feat"},
            }
        },
    )

    mock_repo = MagicMock()
    mock_file = MagicMock()
    mock_file.filename = "src/foo.py"
    mock_file.patch = "diff line"
    mock_compare = MagicMock()
    mock_compare.files = [mock_file]
    mock_repo.compare.return_value = mock_compare
    mock_repo.get_contents.return_value = MagicMock(decoded_content=b"reviewer:\n  enabled: true")

    settings = MagicMock()
    settings.GITHUB_TOKEN = "token"
    mock_check_run = MagicMock()

    reviewer_config = ReviewerConfig(enabled=True, block_on=[])

    with (
        patch("booty.reviewer.runner.get_verifier_repo", return_value=mock_repo),
        patch("booty.reviewer.runner.get_reviewer_config", return_value=reviewer_config),
        patch("booty.reviewer.runner.apply_reviewer_env_overrides", return_value=reviewer_config),
        patch("booty.reviewer.runner.load_booty_config_from_content") as _,
        patch("booty.reviewer.runner.create_reviewer_check_run", return_value=mock_check_run),
        patch("booty.reviewer.runner.edit_check_run") as mock_edit,
        patch("booty.reviewer.runner.post_reviewer_comment") as mock_post,
        patch("booty.reviewer.runner.run_review", return_value=_make_result("APPROVED")),
    ):
        await process_reviewer_job(job, settings)

    final_edit = [c for c in mock_edit.call_args_list if c[1].get("conclusion")][-1]
    assert final_edit[1]["conclusion"] == "success"
    assert final_edit[1]["output"]["title"] == "Reviewer approved"


@pytest.mark.asyncio
async def test_process_reviewer_job_blocked_failure_and_comment() -> None:
    """process_reviewer_job with BLOCKED → conclusion=failure, title=Reviewer blocked; post_reviewer_comment called."""
    from booty.reviewer.config import ReviewerConfig
    from booty.reviewer.job import ReviewerJob
    from booty.reviewer.runner import process_reviewer_job

    job = ReviewerJob(
        job_id="r-2",
        owner="o",
        repo_name="r",
        pr_number=2,
        head_sha="def456",
        head_ref="feat",
        repo_url="https://github.com/o/r",
        installation_id=1,
        payload={
            "pull_request": {
                "title": "PR",
                "body": "",
                "base": {"sha": "base456", "ref": "main"},
                "head": {"sha": "def456", "ref": "feat"},
            }
        },
    )

    mock_repo = MagicMock()
    mock_file = MagicMock()
    mock_file.filename = "src/bar.py"
    mock_file.patch = "diff"
    mock_compare = MagicMock()
    mock_compare.files = [mock_file]
    mock_repo.compare.return_value = mock_compare
    mock_repo.get_contents.return_value = MagicMock(decoded_content=b"reviewer:\n  enabled: true")

    settings = MagicMock()
    settings.GITHUB_TOKEN = "token"
    mock_check_run = MagicMock()

    reviewer_config = ReviewerConfig(enabled=True, block_on=[])

    with (
        patch("booty.reviewer.runner.get_verifier_repo", return_value=mock_repo),
        patch("booty.reviewer.runner.get_reviewer_config", return_value=reviewer_config),
        patch("booty.reviewer.runner.apply_reviewer_env_overrides", return_value=reviewer_config),
        patch("booty.reviewer.runner.load_booty_config_from_content") as _,
        patch("booty.reviewer.runner.create_reviewer_check_run", return_value=mock_check_run),
        patch("booty.reviewer.runner.edit_check_run") as mock_edit,
        patch("booty.reviewer.runner.post_reviewer_comment") as mock_post,
        patch("booty.reviewer.runner.run_review", return_value=_make_result("BLOCKED", ["Tests"])),
    ):
        await process_reviewer_job(job, settings)

    final_edit = [c for c in mock_edit.call_args_list if c[1].get("conclusion")][-1]
    assert final_edit[1]["conclusion"] == "failure"
    assert final_edit[1]["output"]["title"] == "Reviewer blocked"

    mock_post.assert_called_once()
    call_body = mock_post.call_args[0][3]
    assert "<!-- booty-reviewer -->" in call_body
