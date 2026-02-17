"""Tests for main-branch verification (MainVerificationQueue, process_main_verification_job)."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from booty.release_governor.main_verify import (
    MainVerificationJob,
    MainVerificationQueue,
    _dedup_key,
    process_main_verification_job,
)
from booty.test_runner.config import ReleaseGovernorConfig


def test_dedup_key():
    """_dedup_key produces consistent key for repo+sha."""
    assert _dedup_key("owner/repo", "abc123") == "owner/repo:main:abc123"
    assert _dedup_key("a/b", "x") != _dedup_key("a/b", "y")


def test_main_verification_job_dataclass():
    """MainVerificationJob has required fields."""
    job = MainVerificationJob(
        repo_full_name="owner/repo",
        head_sha="abc123",
        repo_url="https://github.com/owner/repo",
        delivery_id="delivery-1",
    )
    assert job.repo_full_name == "owner/repo"
    assert job.head_sha == "abc123"


@pytest.mark.asyncio
async def test_main_verification_queue_enqueue_dedup():
    """Queue rejects duplicate repo+head_sha."""
    queue = MainVerificationQueue(maxsize=10)
    # Don't start workers — we'll just test enqueue
    job = MainVerificationJob(
        repo_full_name="o/r",
        head_sha="abc123",
        repo_url="https://github.com/o/r",
        delivery_id="d1",
    )
    ok1 = await queue.enqueue(job)
    assert ok1 is True

    # Same repo+sha = duplicate
    job2 = MainVerificationJob(
        repo_full_name="o/r",
        head_sha="abc123",
        repo_url="https://github.com/o/r",
        delivery_id="d2",
    )
    ok2 = await queue.enqueue(job2)
    assert ok2 is False

    # Different sha = not duplicate
    job3 = MainVerificationJob(
        repo_full_name="o/r",
        head_sha="def456",
        repo_url="https://github.com/o/r",
        delivery_id="d3",
    )
    ok3 = await queue.enqueue(job3)
    assert ok3 is True


@pytest.mark.asyncio
async def test_main_verification_queue_is_duplicate():
    """is_duplicate reflects enqueued/processed jobs."""
    queue = MainVerificationQueue(maxsize=10)
    assert queue.is_duplicate("o/r", "abc") is False
    job = MainVerificationJob("o/r", "abc", "https://github.com/o/r", "")
    await queue.enqueue(job)
    assert queue.is_duplicate("o/r", "abc") is True
    assert queue.is_duplicate("o/r", "def") is False


@pytest.mark.asyncio
async def test_process_main_verification_job_skips_already_processed():
    """process_main_verification_job skips when delivery_id already recorded."""
    job = MainVerificationJob(
        repo_full_name="owner/repo",
        head_sha="abc123",
        repo_url="https://github.com/owner/repo",
        delivery_id="del-1",
    )
    with patch(
        "booty.release_governor.main_verify.has_delivery_id", return_value=True
    ):
        with patch(
            "booty.release_governor.main_verify.load_booty_config_for_repo"
        ) as mock_load:
            mock_load.side_effect = AssertionError("should not be called")
            await process_main_verification_job(job)


@pytest.mark.asyncio
async def test_process_main_verification_job_skips_no_governor_config():
    """process_main_verification_job skips when no release_governor config."""
    job = MainVerificationJob(
        repo_full_name="owner/repo",
        head_sha="abc123",
        repo_url="https://github.com/owner/repo",
        delivery_id="del-1",
    )
    with patch(
        "booty.release_governor.main_verify.has_delivery_id", return_value=False
    ):
        with patch(
            "booty.release_governor.main_verify.load_booty_config_for_repo",
            return_value=None,
        ):
            await process_main_verification_job(job)


@pytest.mark.asyncio
async def test_process_main_verification_job_skips_governor_disabled():
    """process_main_verification_job skips when Governor disabled."""
    job = MainVerificationJob(
        repo_full_name="owner/repo",
        head_sha="abc123",
        repo_url="https://github.com/owner/repo",
        delivery_id="del-1",
    )
    mock_config = MagicMock()
    mock_config.release_governor = ReleaseGovernorConfig(
        enabled=False,
        deploy_workflow_name="deploy.yml",
        verification_workflow_name="",
        max_deploys_per_hour=6,
    )

    with patch(
        "booty.release_governor.main_verify.has_delivery_id", return_value=False
    ):
        with patch(
            "booty.release_governor.main_verify.load_booty_config_for_repo",
            return_value=mock_config,
        ):
            await process_main_verification_job(job)


@pytest.mark.asyncio
async def test_process_main_verification_job_verification_passed_applies_governor():
    """When verification passes, Governor decision is applied."""
    job = MainVerificationJob(
        repo_full_name="owner/repo",
        head_sha="abc123",
        repo_url="https://github.com/owner/repo",
        delivery_id="del-1",
    )
    mock_booty_config = MagicMock()
    mock_booty_config.release_governor = ReleaseGovernorConfig(
        enabled=True,
        deploy_workflow_name="deploy.yml",
        verification_workflow_name="",
        max_deploys_per_hour=6,
    )
    mock_booty_config.setup_command = None
    mock_booty_config.install_command = None
    mock_booty_config.test_command = "pytest"

    mock_workspace = MagicMock()
    mock_workspace.path = "/tmp/ws"
    mock_workspace.__aenter__ = AsyncMock(return_value=mock_workspace)
    mock_workspace.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "booty.release_governor.main_verify.has_delivery_id", return_value=False
    ):
        with patch(
            "booty.release_governor.main_verify.load_booty_config_for_repo",
            return_value=mock_booty_config,
        ):
            with patch(
                "booty.release_governor.main_verify.prepare_verification_workspace",
                return_value=mock_workspace,
            ):
                with patch(
                    "booty.release_governor.main_verify.load_booty_config",
                    return_value=mock_booty_config,
                ):
                    with patch(
                        "booty.release_governor.main_verify.execute_tests",
                        new_callable=AsyncMock,
                        return_value=MagicMock(exit_code=0),
                    ):
                        with patch(
                            "booty.release_governor.main_verify.simulate_decision_for_cli"
                        ) as mock_sim:
                            from booty.release_governor.decision import Decision

                            mock_sim.return_value = (
                                Decision("ALLOW", "ok", "LOW", "abc123"),
                                [],
                            )
                            with patch(
                                "booty.release_governor.main_verify.apply_governor_decision"
                            ) as mock_apply:
                                with patch(
                                    "booty.release_governor.main_verify.Github"
                                ) as mock_gh:
                                    mock_gh.return_value.get_repo.return_value = MagicMock()
                                    with patch(
                                        "booty.release_governor.main_verify.get_settings"
                                    ) as mock_settings:
                                        mock_settings.return_value.GITHUB_TOKEN = "tok"
                                        with patch(
                                            "booty.release_governor.main_verify.get_state_dir"
                                        ) as mock_state_dir:
                                            import tempfile

                                            with tempfile.TemporaryDirectory() as d:
                                                mock_state_dir.return_value = Path(d)
                                                await process_main_verification_job(job)

    mock_apply.assert_called_once()
    call_args = mock_apply.call_args[0]
    call_kw = mock_apply.call_args[1]
    assert call_args[1] == "abc123"  # head_sha is second positional arg
    assert call_args[2].outcome == "ALLOW"  # decision is third positional arg


@pytest.mark.asyncio
async def test_process_main_verification_job_verification_failed_posts_hold():
    """When verification fails, HOLD with verification_failed is posted."""
    job = MainVerificationJob(
        repo_full_name="owner/repo",
        head_sha="abc123",
        repo_url="https://github.com/owner/repo",
        delivery_id="del-1",
    )
    mock_booty_config = MagicMock()
    mock_booty_config.release_governor = ReleaseGovernorConfig(
        enabled=True,
        deploy_workflow_name="deploy.yml",
        verification_workflow_name="",
        max_deploys_per_hour=6,
    )
    mock_booty_config.setup_command = None
    mock_booty_config.install_command = None

    mock_workspace = MagicMock()
    mock_workspace.path = "/tmp/ws"
    mock_workspace.__aenter__ = AsyncMock(return_value=mock_workspace)
    mock_workspace.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "booty.release_governor.main_verify.has_delivery_id", return_value=False
    ):
        with patch(
            "booty.release_governor.main_verify.load_booty_config_for_repo",
            return_value=mock_booty_config,
        ):
            with patch(
                "booty.release_governor.main_verify.prepare_verification_workspace",
                return_value=mock_workspace,
            ):
                with patch(
                    "booty.release_governor.main_verify.load_booty_config",
                    return_value=mock_booty_config,
                ):
                    with patch(
                        "booty.release_governor.main_verify.execute_tests",
                        new_callable=AsyncMock,
                        return_value=MagicMock(exit_code=1),
                    ):
                        with patch(
                            "booty.release_governor.main_verify.post_hold_status"
                        ) as mock_post_hold:
                            with patch(
                                "booty.release_governor.main_verify.Github"
                            ) as mock_gh:
                                mock_gh.return_value.get_repo.return_value = MagicMock()
                                with patch(
                                    "booty.release_governor.main_verify.get_settings"
                                ) as mock_settings:
                                    mock_settings.return_value.GITHUB_TOKEN = "tok"
                                    with patch(
                                        "booty.release_governor.main_verify.get_state_dir"
                                    ) as mock_state_dir:
                                        import tempfile

                                        with tempfile.TemporaryDirectory() as d:
                                            mock_state_dir.return_value = Path(d)
                                            await process_main_verification_job(job)

    mock_post_hold.assert_called_once()
    call_args = mock_post_hold.call_args[0]
    assert call_args[2].reason == "verification_failed"
