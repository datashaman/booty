"""Tests for push handler enqueuing MainVerificationJob on push to main."""

import hmac
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from booty.main import app
from booty.release_governor.main_verify import MainVerificationJob, MainVerificationQueue


def _sign_payload(payload: dict, secret: str) -> str:
    """Compute X-Hub-Signature-256 for GitHub webhook."""
    body = json.dumps(payload).encode()
    digest = hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return f"sha256={digest}"


@pytest.fixture
def push_main_payload():
    """Minimal push-to-main payload."""
    return {
        "ref": "refs/heads/main",
        "after": "abc123def456",
        "repository": {
            "full_name": "owner/repo",
            "html_url": "https://github.com/owner/repo",
        },
        "commits": [],
    }


@pytest.fixture
def mock_main_verify_queue():
    """Mock MainVerificationQueue that records enqueue calls."""
    queue = MagicMock(spec=MainVerificationQueue)
    queue.enqueue = AsyncMock(return_value=True)
    queue.is_duplicate = MagicMock(return_value=False)
    return queue


def test_push_to_main_enqueues_main_verification_when_governor_enabled(
    push_main_payload, mock_main_verify_queue
):
    """Push to main with Governor enabled enqueues MainVerificationJob."""
    mock_config = MagicMock()
    mock_config.release_governor = MagicMock()
    mock_config.release_governor.enabled = True
    mock_config.release_governor.deploy_workflow_name = "deploy.yml"

    with patch("booty.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = "test-secret"
        mock_settings.return_value.GITHUB_TOKEN = "token"

        with patch(
            "booty.webhooks.load_booty_config_for_repo",
            return_value=mock_config,
        ):
            with patch(
                "booty.test_runner.config.apply_release_governor_env_overrides"
            ) as mock_apply_env:
                mock_apply_env.return_value = mock_config.release_governor

                client = TestClient(app, raise_server_exceptions=False)
                client.get("/health")  # Trigger lifespan
                app.state.main_verification_queue = mock_main_verify_queue

                body = json.dumps(push_main_payload)
                sig = _sign_payload(push_main_payload, "test-secret")

                response = client.post(
                    "/webhooks/github",
                    content=body,
                    headers={
                        "X-GitHub-Event": "push",
                        "X-Hub-Signature-256": sig,
                        "X-GitHub-Delivery": "delivery-123",
                        "Content-Type": "application/json",
                    },
                )

                assert response.status_code == 202
                assert response.json()["event"] == "push"

                mock_main_verify_queue.enqueue.assert_called_once()
                job = mock_main_verify_queue.enqueue.call_args[0][0]
                assert isinstance(job, MainVerificationJob)
                assert job.repo_full_name == "owner/repo"
                assert job.head_sha == "abc123def456"
                assert job.repo_url == "https://github.com/owner/repo"
                assert job.delivery_id == "delivery-123"


def test_push_to_main_ignored_when_not_main(push_main_payload):
    """Push to non-main ref is ignored (no main verification)."""
    payload = {**push_main_payload, "ref": "refs/heads/feature"}
    mock_config = MagicMock()
    mock_config.release_governor = MagicMock()
    mock_config.release_governor.enabled = True
    mock_config.release_governor.deploy_workflow_name = "deploy.yml"

    with patch("booty.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = "test-secret"
        mock_settings.return_value.GITHUB_TOKEN = "token"

        with patch(
            "booty.webhooks.load_booty_config_for_repo",
            return_value=mock_config,
        ):
            mock_queue = MagicMock(spec=MainVerificationQueue)
            mock_queue.enqueue = AsyncMock(return_value=True)
            mock_queue.is_duplicate = MagicMock(return_value=False)

            client = TestClient(app, raise_server_exceptions=False)
            client.get("/health")  # Trigger lifespan
            app.state.main_verification_queue = mock_queue

            body = json.dumps(payload)
            sig = _sign_payload(payload, "test-secret")

            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/webhooks/github",
                content=body,
                headers={
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": sig,
                    "X-GitHub-Delivery": "delivery-123",
                    "Content-Type": "application/json",
                },
            )

            assert response.status_code == 200
            assert response.json().get("reason") == "not_main"
            mock_queue.enqueue.assert_not_called()


def test_push_to_main_no_enqueue_when_governor_disabled(push_main_payload):
    """Push to main with Governor disabled does not enqueue."""
    mock_config = MagicMock()
    mock_config.release_governor = MagicMock()
    mock_config.release_governor.enabled = False
    mock_config.release_governor.deploy_workflow_name = "deploy.yml"

    with patch("booty.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = "test-secret"
        mock_settings.return_value.GITHUB_TOKEN = "token"

        with patch(
            "booty.webhooks.load_booty_config_for_repo",
            return_value=mock_config,
        ):
            with patch(
                "booty.test_runner.config.apply_release_governor_env_overrides"
            ) as mock_apply_env:
                mock_apply_env.return_value = mock_config.release_governor

                mock_queue = MagicMock(spec=MainVerificationQueue)
                mock_queue.enqueue = AsyncMock(return_value=True)
                mock_queue.is_duplicate = MagicMock(return_value=False)

                client = TestClient(app, raise_server_exceptions=False)
                client.get("/health")  # Trigger lifespan
                app.state.main_verification_queue = mock_queue

                body = json.dumps(push_main_payload)
                sig = _sign_payload(push_main_payload, "test-secret")

                response = client.post(
                    "/webhooks/github",
                    content=body,
                    headers={
                        "X-GitHub-Event": "push",
                        "X-Hub-Signature-256": sig,
                        "X-GitHub-Delivery": "delivery-123",
                        "Content-Type": "application/json",
                    },
                )

                assert response.status_code == 202
                mock_queue.enqueue.assert_not_called()


def test_push_to_main_no_enqueue_when_no_after_sha(push_main_payload):
    """Push to main with empty 'after' does not enqueue."""
    payload = {**push_main_payload, "after": ""}
    mock_config = MagicMock()
    mock_config.release_governor = MagicMock()
    mock_config.release_governor.enabled = True
    mock_config.release_governor.deploy_workflow_name = "deploy.yml"

    with patch("booty.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.WEBHOOK_SECRET = "test-secret"
        mock_settings.return_value.GITHUB_TOKEN = "token"

        with patch(
            "booty.webhooks.load_booty_config_for_repo",
            return_value=mock_config,
        ):
            with patch(
                "booty.test_runner.config.apply_release_governor_env_overrides"
            ) as mock_apply_env:
                mock_apply_env.return_value = mock_config.release_governor

                mock_queue = MagicMock(spec=MainVerificationQueue)
                mock_queue.enqueue = AsyncMock(return_value=True)
                mock_queue.is_duplicate = MagicMock(return_value=False)

                client = TestClient(app, raise_server_exceptions=False)
                client.get("/health")  # Trigger lifespan
                app.state.main_verification_queue = mock_queue

                body = json.dumps(payload)
                sig = _sign_payload(payload, "test-secret")

                response = client.post(
                    "/webhooks/github",
                    content=body,
                    headers={
                        "X-GitHub-Event": "push",
                        "X-Hub-Signature-256": sig,
                        "X-GitHub-Delivery": "delivery-123",
                        "Content-Type": "application/json",
                    },
                )

                assert response.status_code == 202
                mock_queue.enqueue.assert_not_called()
