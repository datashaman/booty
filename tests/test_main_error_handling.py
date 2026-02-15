"""Tests for error handling in main.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from booty.main import (
    app,
    process_job,
    _process_verifier_job,
    get_app_version,
    global_exception_handler,
)
from booty.jobs import Job
from booty.verifier import VerifierJob


class TestGetAppVersion:
    """Tests for get_app_version function."""

    def test_get_app_version_success(self):
        """Test getting app version successfully."""
        version = get_app_version()
        assert isinstance(version, str)
        assert len(version) > 0

    @patch("booty.main.version")
    def test_get_app_version_not_found(self, mock_version):
        """Test getting app version when package not found."""
        from importlib.metadata import PackageNotFoundError

        mock_version.side_effect = PackageNotFoundError("booty")
        version = get_app_version()
        assert version == "unknown"


class TestProcessJob:
    """Tests for process_job function."""

    @pytest.mark.asyncio
    async def test_process_job_pipeline_exception(self):
        """Test process_job handles pipeline exceptions."""
        job = Job(
            job_id="test-job-1",
            issue_number=123,
            issue_title="Test Issue",
            issue_body="Test body",
            repo_url="https://github.com/test/repo",
            verifier_retries=0,
        )

        with patch("booty.main.get_settings") as mock_settings, \
             patch("booty.main.prepare_workspace") as mock_workspace, \
             patch("booty.main.process_issue_to_pr") as mock_process, \
             patch("booty.main.post_failure_comment") as mock_comment, \
             patch("booty.main.get_logger") as mock_logger:

            # Setup mocks
            mock_settings.return_value = MagicMock(
                TARGET_REPO_URL="https://github.com/test/repo",
                TARGET_BRANCH="main",
                GITHUB_TOKEN="test-token",
            )

            mock_workspace_instance = MagicMock()
            mock_workspace_instance.path = "/tmp/test"
            mock_workspace_instance.branch = "main"
            mock_workspace.return_value.__aenter__ = AsyncMock(
                return_value=mock_workspace_instance
            )
            mock_workspace.return_value.__aexit__ = AsyncMock(return_value=None)

            # Simulate pipeline exception
            mock_process.side_effect = ValueError("Pipeline error")

            mock_logger_instance = MagicMock()
            mock_logger_instance.bind.return_value = mock_logger_instance
            mock_logger.return_value = mock_logger_instance

            # Execute
            await process_job(job)

            # Verify error was logged
            mock_logger_instance.error.assert_called()
            error_call = mock_logger_instance.error.call_args
            assert "pipeline_exception" in error_call[0]

            # Verify failure comment was posted
            mock_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_job_comment_failure(self):
        """Test process_job handles failure when posting comment fails."""
        job = Job(
            job_id="test-job-2",
            issue_number=456,
            issue_title="Test Issue",
            issue_body="Test body",
            repo_url="https://github.com/test/repo",
            verifier_retries=0,
        )

        with patch("booty.main.get_settings") as mock_settings, \
             patch("booty.main.prepare_workspace") as mock_workspace, \
             patch("booty.main.process_issue_to_pr") as mock_process, \
             patch("booty.main.post_failure_comment") as mock_comment, \
             patch("booty.main.get_logger") as mock_logger:

            # Setup mocks
            mock_settings.return_value = MagicMock(
                TARGET_REPO_URL="https://github.com/test/repo",
                TARGET_BRANCH="main",
                GITHUB_TOKEN="test-token",
            )

            mock_workspace_instance = MagicMock()
            mock_workspace_instance.path = "/tmp/test"
            mock_workspace_instance.branch = "main"
            mock_workspace.return_value.__aenter__ = AsyncMock(
                return_value=mock_workspace_instance
            )
            mock_workspace.return_value.__aexit__ = AsyncMock(return_value=None)

            # Simulate both pipeline and comment failures
            mock_process.side_effect = ValueError("Pipeline error")
            mock_comment.side_effect = Exception("Comment posting failed")

            mock_logger_instance = MagicMock()
            mock_logger_instance.bind.return_value = mock_logger_instance
            mock_logger.return_value = mock_logger_instance

            # Execute
            await process_job(job)

            # Verify both errors were logged
            assert mock_logger_instance.error.call_count >= 2

    @pytest.mark.asyncio
    async def test_process_job_unexpected_error(self):
        """Test process_job handles unexpected errors."""
        job = Job(
            job_id="test-job-3",
            issue_number=789,
            issue_title="Test Issue",
            issue_body="Test body",
            repo_url="https://github.com/test/repo",
            verifier_retries=0,
        )

        with patch("booty.main.get_settings") as mock_settings, \
             patch("booty.main.get_logger") as mock_logger:

            # Setup mocks to raise unexpected error
            mock_settings.side_effect = RuntimeError("Unexpected error")

            mock_logger_instance = MagicMock()
            mock_logger_instance.bind.return_value = mock_logger_instance
            mock_logger.return_value = mock_logger_instance

            # Execute and expect exception
            with pytest.raises(RuntimeError):
                await process_job(job)

            # Verify error was logged
            mock_logger_instance.error.assert_called()


class TestProcessVerifierJob:
    """Tests for _process_verifier_job function."""

    @pytest.mark.asyncio
    async def test_process_verifier_job_error(self):
        """Test _process_verifier_job handles errors."""
        job = VerifierJob(
            job_id="verifier-job-1",
            pr_number=100,
            repo_url="https://github.com/test/repo",
            branch="test-branch",
            original_job_id="original-job-1",
        )

        with patch("booty.main.get_settings") as mock_settings, \
             patch("booty.main.process_verifier_job") as mock_process, \
             patch("booty.main.get_logger") as mock_logger:

            # Setup mocks
            mock_settings.return_value = MagicMock()
            mock_process.side_effect = Exception("Verifier error")

            mock_logger_instance = MagicMock()
            mock_logger_instance.bind.return_value = mock_logger_instance
            mock_logger.return_value = mock_logger_instance

            # Execute and expect exception
            with pytest.raises(Exception):
                await _process_verifier_job(job)

            # Verify error was logged
            mock_logger_instance.error.assert_called()
            error_call = mock_logger_instance.error.call_args
            assert "verifier_job_processing_error" in error_call[0]


class TestGlobalExceptionHandler:
    """Tests for global exception handler."""

    @pytest.mark.asyncio
    async def test_global_exception_handler(self):
        """Test global exception handler logs and returns error response."""
        mock_request = MagicMock()
        mock_request.url.path = "/test/path"
        mock_request.method = "GET"

        test_exception = ValueError("Test error")

        with patch("booty.main.get_logger") as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance

            response = await global_exception_handler(mock_request, test_exception)

            # Verify error was logged
            mock_logger_instance.error.assert_called_once()
            error_call = mock_logger_instance.error.call_args
            assert "unhandled_exception" in error_call[0]

            # Verify response
            assert response.status_code == 500
            assert "error" in response.body.decode()


class TestEndpoints:
    """Tests for API endpoints error handling."""

    def test_health_endpoint(self):
        """Test health endpoint returns OK."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_jobs_endpoint_not_initialized(self):
        """Test jobs endpoint when queue not initialized."""
        with patch("booty.main.job_queue", None):
            client = TestClient(app)
            response = client.get("/jobs")
            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert data["jobs"] == []

    def test_info_endpoint_not_initialized(self):
        """Test info endpoint when app not initialized."""
        with patch("booty.main.job_queue", None), \
             patch("booty.main.app_start_time", None):
            client = TestClient(app)
            response = client.get("/info")
            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert data["version"] == get_app_version()
            assert data["uptime_seconds"] == 0
