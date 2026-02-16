"""Tests for Sentry integration — capture_exception on job/verifier failures."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from booty.jobs import Job
from booty.main import process_job


@pytest.mark.asyncio
async def test_process_job_capture_exception_on_pipeline_crash():
    """When process_issue_to_pr raises, capture_exception is called before post_failure_comment."""
    job = Job(
        job_id="test-job-1",
        issue_url="https://github.com/owner/repo/issues/1",
        issue_number=1,
        payload={
            "repository": {
                "owner": {"login": "owner"},
                "name": "repo",
                "html_url": "https://github.com/owner/repo",
            },
        },
    )

    mock_workspace = MagicMock()
    mock_workspace.path = "/tmp/test"
    mock_workspace.repo = None
    mock_workspace.branch = "main"

    mock_settings = MagicMock()
    mock_settings.TARGET_REPO_URL = "https://github.com/owner/repo"
    mock_settings.TARGET_BRANCH = "main"
    mock_settings.GITHUB_TOKEN = "test-token"

    mock_plan = MagicMock()
    mock_plan.goal = "test goal"
    mock_plan.steps = []
    mock_plan.handoff_to_builder = MagicMock()
    mock_plan.handoff_to_builder.commit_message_hint = "fix: test"
    mock_plan.handoff_to_builder.pr_title = "Test PR"

    with (
        patch("booty.main.process_issue_to_pr", new_callable=AsyncMock) as mock_process,
        patch("booty.main.prepare_workspace") as mock_prepare,
        patch("booty.main.post_failure_comment") as mock_post,
        patch("booty.main.sentry_sdk") as mock_sentry,
        patch("booty.main.get_settings", return_value=mock_settings),
        patch("booty.main.load_plan", return_value=mock_plan),
    ):
        mock_process.side_effect = ValueError("pipeline crash")
        mock_prepare.return_value.__aenter__ = AsyncMock(return_value=mock_workspace)
        mock_prepare.return_value.__aexit__ = AsyncMock(return_value=None)

        await process_job(job)

        mock_sentry.set_tag.assert_any_call("job_id", "test-job-1")
        mock_sentry.set_tag.assert_any_call("issue_number", "1")
        mock_sentry.capture_exception.assert_called_once()
        mock_post.assert_called_once()
