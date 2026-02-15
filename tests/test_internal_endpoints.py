"""Tests for internal test endpoints — authentication and rate limiting."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from booty.main import app, internal_endpoint_limiter


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before each test."""
    internal_endpoint_limiter.requests.clear()
    yield
    internal_endpoint_limiter.requests.clear()


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.SENTRY_ENVIRONMENT = "development"
    settings.INTERNAL_TEST_TOKEN = ""
    return settings


def test_sentry_test_endpoint_no_auth_in_dev(client, mock_settings):
    """In development without token configured, endpoint should work without auth."""
    with patch("booty.main.get_settings", return_value=mock_settings):
        response = client.get("/internal/sentry-test")
        # ValueError is caught by FastAPI and returned as 500
        assert response.status_code == 500


def test_sentry_test_endpoint_requires_token_when_configured(client, mock_settings):
    """When INTERNAL_TEST_TOKEN is set, endpoint requires matching token."""
    mock_settings.INTERNAL_TEST_TOKEN = "secret-token-123"
    
    with patch("booty.main.get_settings", return_value=mock_settings):
        # Missing token
        response = client.get("/internal/sentry-test")
        assert response.status_code == 401
        assert "Invalid or missing X-Internal-Token" in response.json()["detail"]
        
        # Wrong token
        response = client.get(
            "/internal/sentry-test",
            headers={"X-Internal-Token": "wrong-token"}
        )
        assert response.status_code == 401
        
        # Correct token - should raise ValueError (500)
        response = client.get(
            "/internal/sentry-test",
            headers={"X-Internal-Token": "secret-token-123"}
        )
        assert response.status_code == 500


def test_sentry_test_endpoint_requires_token_in_production(client, mock_settings):
    """In production, endpoint requires INTERNAL_TEST_TOKEN to be set and matching."""
    mock_settings.SENTRY_ENVIRONMENT = "production"
    mock_settings.INTERNAL_TEST_TOKEN = ""
    
    with patch("booty.main.get_settings", return_value=mock_settings):
        # Disabled without token
        response = client.get("/internal/sentry-test")
        assert response.status_code == 403
        assert "Test endpoint disabled in production" in response.json()["detail"]
    
    # With token configured
    mock_settings.INTERNAL_TEST_TOKEN = "prod-token"
    with patch("booty.main.get_settings", return_value=mock_settings):
        # Missing token
        response = client.get("/internal/sentry-test")
        assert response.status_code == 401
        
        # Correct token - should raise ValueError (500)
        response = client.get(
            "/internal/sentry-test",
            headers={"X-Internal-Token": "prod-token"}
        )
        assert response.status_code == 500


def test_sentry_test_endpoint_rate_limiting(client, mock_settings):
    """Endpoint should enforce rate limiting of 5 requests per 60 seconds."""
    with patch("booty.main.get_settings", return_value=mock_settings):
        # First 5 requests should succeed (return 500 from ValueError)
        for i in range(5):
            response = client.get("/internal/sentry-test")
            assert response.status_code == 500, f"Request {i+1} should succeed with 500"
        
        # 6th request should be rate limited
        response = client.get("/internal/sentry-test")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
        assert "5 requests per 60 seconds" in response.json()["detail"]


def test_rate_limiter_sliding_window():
    """Rate limiter should use sliding window, not fixed window."""
    from datetime import datetime, timedelta, timezone
    from booty.main import SimpleRateLimiter
    
    limiter = SimpleRateLimiter(max_requests=3, window_seconds=10)
    
    # Make 3 requests at T=0
    assert not limiter.is_rate_limited("test-ip")
    assert not limiter.is_rate_limited("test-ip")
    assert not limiter.is_rate_limited("test-ip")
    
    # 4th request should be limited
    assert limiter.is_rate_limited("test-ip")
    
    # Manually age out old requests by modifying timestamps
    old_time = datetime.now(timezone.utc) - timedelta(seconds=11)
    limiter.requests["test-ip"] = [old_time, old_time]
    
    # Should allow new requests after window expires
    assert not limiter.is_rate_limited("test-ip")


def test_rate_limiter_per_ip_isolation():
    """Rate limiter should track limits per IP independently."""
    from booty.main import SimpleRateLimiter
    
    limiter = SimpleRateLimiter(max_requests=2, window_seconds=60)
    
    # IP1 makes 2 requests
    assert not limiter.is_rate_limited("192.168.1.1")
    assert not limiter.is_rate_limited("192.168.1.1")
    assert limiter.is_rate_limited("192.168.1.1")  # 3rd is limited
    
    # IP2 should still be able to make requests
    assert not limiter.is_rate_limited("192.168.1.2")
    assert not limiter.is_rate_limited("192.168.1.2")
    assert limiter.is_rate_limited("192.168.1.2")  # 3rd is limited


def test_rate_limiter_cleanup():
    """Rate limiter should clean up old entries to prevent memory growth."""
    from datetime import datetime, timedelta, timezone
    from booty.main import SimpleRateLimiter
    
    limiter = SimpleRateLimiter(max_requests=5, window_seconds=60)
    
    # Add requests for multiple IPs
    limiter.is_rate_limited("ip1")
    limiter.is_rate_limited("ip2")
    limiter.is_rate_limited("ip3")
    
    assert len(limiter.requests) == 3
    
    # Age out all requests
    old_time = datetime.now(timezone.utc) - timedelta(seconds=150)
    for ip in limiter.requests:
        limiter.requests[ip] = [old_time]
    
    # Cleanup should remove old entries
    limiter.cleanup_old_entries()
    assert len(limiter.requests) == 0
