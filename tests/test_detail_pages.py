"""Tests for detail page routes and SSE streaming functionality."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from booty.main import app
from booty.detail_pages import get_job_status, stream_job_events


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis client for job status retrieval."""
    with patch("booty.detail_pages.redis_client") as mock:
        yield mock


class TestDetailPageRoutes:
    """Test detail page HTTP routes."""

    def test_verifier_detail_page_renders(self, client):
        """Test that verifier detail page returns HTML."""
        response = client.get("/detail/verifier/test-job-123")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Verifier Job Details" in response.content
        assert b"test-job-123" in response.content

    def test_main_verify_detail_page_renders(self, client):
        """Test that main verification detail page returns HTML."""
        response = client.get("/detail/main-verify/test-delivery-456")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Main Verification" in response.content
        assert b"test-delivery-456" in response.content

    def test_governor_detail_page_renders(self, client):
        """Test that governor detail page returns HTML."""
        response = client.get("/detail/governor/test-delivery-789")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Release Governor" in response.content
        assert b"test-delivery-789" in response.content


class TestSSEStreaming:
    """Test Server-Sent Events streaming for realtime updates."""

    def test_verifier_sse_stream_job_running(self, client, mock_redis):
        """Test SSE stream returns events for a running job."""
        # Mock job status in Redis
        mock_redis.get.return_value = json.dumps({
            "job_id": "test-job-123",
            "status": "running",
            "progress": "Running tests...",
            "test_output": ["test_foo.py::test_bar PASSED", "test_baz.py::test_qux RUNNING"]
        }).encode()

        with client.stream("GET", "/detail/verifier/test-job-123/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            
            # Read first event
            lines = []
            for line in response.iter_lines():
                lines.append(line)
                if line == "":  # Empty line marks end of event
                    break
            
            # Verify SSE format
            event_data = None
            for line in lines:
                if line.startswith("data: "):
                    event_data = json.loads(line[6:])
                    break
            
            assert event_data is not None
            assert event_data["job_id"] == "test-job-123"
            assert event_data["status"] == "running"

    def test_verifier_sse_stream_job_completed(self, client, mock_redis):
        """Test SSE stream handles completed jobs."""
        mock_redis.get.return_value = json.dumps({
            "job_id": "test-job-123",
            "status": "completed",
            "conclusion": "success",
            "test_output": ["All tests passed"]
        }).encode()

        with client.stream("GET", "/detail/verifier/test-job-123/stream") as response:
            assert response.status_code == 200
            
            lines = []
            for line in response.iter_lines():
                lines.append(line)
                if "completed" in line:
                    break
            
            # Should contain completion event
            assert any("completed" in line for line in lines)

    def test_verifier_sse_stream_job_not_found(self, client, mock_redis):
        """Test SSE stream handles missing jobs gracefully."""
        mock_redis.get.return_value = None

        with client.stream("GET", "/detail/verifier/nonexistent-job/stream") as response:
            assert response.status_code == 200
            
            lines = []
            for line in response.iter_lines():
                lines.append(line)
                if "not_found" in line or len(lines) > 10:
                    break
            
            # Should send not_found event
            event_text = "\n".join(lines)
            assert "not_found" in event_text or "error" in event_text

    def test_main_verify_sse_stream(self, client, mock_redis):
        """Test SSE stream for main verification flow."""
        mock_redis.get.return_value = json.dumps({
            "delivery_id": "test-delivery-456",
            "status": "running",
            "stage": "verifier",
            "verifier_status": "running",
            "governor_status": "pending"
        }).encode()

        with client.stream("GET", "/detail/main-verify/test-delivery-456/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

    def test_governor_sse_stream(self, client, mock_redis):
        """Test SSE stream for governor decision flow."""
        mock_redis.get.return_value = json.dumps({
            "delivery_id": "test-delivery-789",
            "status": "evaluating",
            "decision": None,
            "checks": ["verifier: success", "security: success"]
        }).encode()

        with client.stream("GET", "/detail/governor/test-delivery-789/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]


class TestJobStatusRetrieval:
    """Test job status retrieval from Redis."""

    @pytest.mark.asyncio
    async def test_get_job_status_found(self, mock_redis):
        """Test retrieving existing job status."""
        job_data = {
            "job_id": "test-job-123",
            "status": "running",
            "progress": "50%"
        }
        mock_redis.get.return_value = json.dumps(job_data).encode()

        status = await get_job_status("verifier", "test-job-123")
        
        assert status is not None
        assert status["job_id"] == "test-job-123"
        assert status["status"] == "running"
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, mock_redis):
        """Test retrieving non-existent job status."""
        mock_redis.get.return_value = None

        status = await get_job_status("verifier", "nonexistent-job")
        
        assert status is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_status_invalid_json(self, mock_redis):
        """Test handling of corrupted job data."""
        mock_redis.get.return_value = b"invalid json {{"

        status = await get_job_status("verifier", "corrupted-job")
        
        # Should return None or handle gracefully
        assert status is None or isinstance(status, dict)


class TestURLConstruction:
    """Test detail URL construction helpers."""

    def test_construct_verifier_detail_url(self):
        """Test constructing verifier detail URLs."""
        from booty.detail_pages import construct_detail_url
        
        url = construct_detail_url("verifier", "test-job-123", base_url="https://booty.example.com")
        assert url == "https://booty.example.com/detail/verifier/test-job-123"

    def test_construct_main_verify_detail_url(self):
        """Test constructing main verification detail URLs."""
        from booty.detail_pages import construct_detail_url
        
        url = construct_detail_url("main-verify", "test-delivery-456", base_url="https://booty.example.com")
        assert url == "https://booty.example.com/detail/main-verify/test-delivery-456"

    def test_construct_governor_detail_url(self):
        """Test constructing governor detail URLs."""
        from booty.detail_pages import construct_detail_url
        
        url = construct_detail_url("governor", "test-delivery-789", base_url="https://booty.example.com")
        assert url == "https://booty.example.com/detail/governor/test-delivery-789"

    def test_construct_detail_url_no_base_url(self):
        """Test URL construction without base URL returns None."""
        from booty.detail_pages import construct_detail_url
        
        url = construct_detail_url("verifier", "test-job-123", base_url=None)
        assert url is None

    def test_construct_detail_url_empty_base_url(self):
        """Test URL construction with empty base URL returns None."""
        from booty.detail_pages import construct_detail_url
        
        url = construct_detail_url("verifier", "test-job-123", base_url="")
        assert url is None


class TestDetailPageIntegration:
    """Integration tests for detail pages with other components."""

    @patch("booty.detail_pages.redis_client")
    def test_verifier_detail_page_with_real_job_data(self, mock_redis, client):
        """Test detail page rendering with realistic job data."""
        job_data = {
            "job_id": "verifier-abc123",
            "status": "running",
            "repo": "org/repo",
            "ref": "refs/heads/feature-branch",
            "sha": "abc123def456",
            "started_at": "2024-01-15T10:30:00Z",
            "test_output": [
                "test_foo.py::test_bar PASSED",
                "test_foo.py::test_baz PASSED",
                "test_qux.py::test_integration RUNNING"
            ],
            "progress": "Running tests... (2/3 passed)"
        }
        mock_redis.get.return_value = json.dumps(job_data).encode()

        response = client.get("/detail/verifier/verifier-abc123")
        assert response.status_code == 200
        assert b"verifier-abc123" in response.content
        assert b"org/repo" in response.content

    @patch("booty.detail_pages.redis_client")
    def test_main_verify_detail_page_with_governor_hold(self, mock_redis, client):
        """Test main verification page showing governor HOLD decision."""
        delivery_data = {
            "delivery_id": "main-verify-xyz789",
            "status": "completed",
            "repo": "org/repo",
            "ref": "refs/heads/main",
            "sha": "xyz789abc123",
            "verifier_status": "success",
            "governor_status": "hold",
            "governor_decision": "HOLD",
            "governor_reason": "Waiting for manual approval",
            "completed_at": "2024-01-15T10:45:00Z"
        }
        mock_redis.get.return_value = json.dumps(delivery_data).encode()

        response = client.get("/detail/main-verify/main-verify-xyz789")
        assert response.status_code == 200
        assert b"main-verify-xyz789" in response.content
        assert b"HOLD" in response.content or b"hold" in response.content

    def test_detail_page_graceful_degradation_no_redis(self, client):
        """Test detail pages work even when Redis is unavailable."""
        with patch("booty.detail_pages.redis_client", None):
            response = client.get("/detail/verifier/test-job-123")
            # Should still render page, just without live data
            assert response.status_code == 200
            assert b"Verifier Job Details" in response.content


class TestStreamJobEvents:
    """Test the stream_job_events async generator."""

    @pytest.mark.asyncio
    async def test_stream_job_events_yields_updates(self, mock_redis):
        """Test that stream_job_events yields job updates."""
        # Simulate job progressing through states
        states = [
            {"status": "running", "progress": "Starting..."},
            {"status": "running", "progress": "Running tests..."},
            {"status": "completed", "conclusion": "success"}
        ]
        
        mock_redis.get.side_effect = [
            json.dumps(state).encode() for state in states
        ]

        events = []
        count = 0
        async for event in stream_job_events("verifier", "test-job-123"):
            events.append(event)
            count += 1
            if count >= 3:  # Limit iterations for test
                break
        
        assert len(events) >= 1
        assert all(isinstance(event, dict) for event in events)

    @pytest.mark.asyncio
    async def test_stream_job_events_stops_on_completion(self, mock_redis):
        """Test that streaming stops when job completes."""
        mock_redis.get.return_value = json.dumps({
            "status": "completed",
            "conclusion": "success"
        }).encode()

        events = []
        async for event in stream_job_events("verifier", "test-job-123"):
            events.append(event)
            if event.get("status") == "completed":
                break
        
        # Should have received completion event
        assert any(e.get("status") == "completed" for e in events)

    @pytest.mark.asyncio
    async def test_stream_job_events_handles_not_found(self, mock_redis):
        """Test streaming handles job not found."""
        mock_redis.get.return_value = None

        events = []
        count = 0
        async for event in stream_job_events("verifier", "nonexistent-job"):
            events.append(event)
            count += 1
            if count >= 2:  # Should send not_found and stop
                break
        
        # Should indicate job not found
        assert len(events) >= 1
        assert any("not_found" in str(e) or e.get("status") == "not_found" for e in events)
