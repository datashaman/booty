"""Tests for release state store and delivery ID cache."""

import os

import pytest

from booty.release_governor.store import (
    ReleaseState,
    get_state_dir,
    has_delivery_id,
    load_release_state,
    record_delivery_id,
    save_release_state,
)


@pytest.fixture
def temp_state_dir(tmp_path, monkeypatch):
    """Use temp dir for state."""
    monkeypatch.setenv("RELEASE_GOVERNOR_STATE_DIR", str(tmp_path))
    yield get_state_dir()


def test_load_returns_defaults_when_missing(temp_state_dir) -> None:
    """load_release_state returns defaults when release.json missing."""
    s = load_release_state(temp_state_dir)
    assert s.production_sha_current is None
    assert s.last_deploy_result == "pending"


def test_save_load_roundtrip(temp_state_dir) -> None:
    """save_release_state then load_release_state round-trip."""
    s = ReleaseState(
        production_sha_current="abc123",
        production_sha_previous="prev456",
        last_deploy_attempt_sha="abc123",
        last_deploy_time="2026-01-01T00:00:00Z",
        last_deploy_result="success",
        last_health_check=None,
    )
    save_release_state(temp_state_dir, s)
    s2 = load_release_state(temp_state_dir)
    assert s2.production_sha_current == "abc123"
    assert s2.production_sha_previous == "prev456"
    assert s2.last_deploy_result == "success"


def test_has_delivery_id_false_for_new(temp_state_dir) -> None:
    """has_delivery_id returns False for new (repo, sha)."""
    assert has_delivery_id(temp_state_dir, "owner/repo", "abc123") is False


def test_record_then_has_delivery_id(temp_state_dir) -> None:
    """record_delivery_id then has_delivery_id returns True."""
    record_delivery_id(temp_state_dir, "owner/repo", "abc123", "deliv-1")
    assert has_delivery_id(temp_state_dir, "owner/repo", "abc123") is True


def test_different_repo_sha_independent(temp_state_dir) -> None:
    """Different (repo, sha) pairs are independent."""
    record_delivery_id(temp_state_dir, "a/b", "sha1", "d1")
    record_delivery_id(temp_state_dir, "c/d", "sha2", "d2")
    assert has_delivery_id(temp_state_dir, "a/b", "sha1") is True
    assert has_delivery_id(temp_state_dir, "c/d", "sha2") is True
    assert has_delivery_id(temp_state_dir, "a/b", "sha2") is False
    assert has_delivery_id(temp_state_dir, "c/d", "sha1") is False


def test_get_state_dir_creates_directory(tmp_path, monkeypatch) -> None:
    """get_state_dir creates directory when missing."""
    d = tmp_path / "new_state"
    assert not d.exists()
    monkeypatch.setenv("RELEASE_GOVERNOR_STATE_DIR", str(d))
    state_dir = get_state_dir()
    assert state_dir.exists()
    assert state_dir.is_dir()
