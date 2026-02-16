"""Tests for security override persistence."""

import json

import pytest

from booty.security.override import persist_override


@pytest.fixture
def temp_state_dir(tmp_path, monkeypatch):
    """Use temp dir for state."""
    monkeypatch.setenv("RELEASE_GOVERNOR_STATE_DIR", str(tmp_path))
    from booty.release_governor.store import get_state_dir
    yield get_state_dir()


def test_persist_override_creates_file(temp_state_dir) -> None:
    """persist_override writes to security_overrides.json with correct schema."""
    persist_override("owner/repo", "abc123", [".github/workflows/ci.yml"])
    path = temp_state_dir / "security_overrides.json"
    assert path.exists()
    with open(path) as f:
        data = json.load(f)
    key = "owner/repo:abc123"
    assert key in data
    entry = data[key]
    assert entry["risk_override"] == "HIGH"
    assert entry["reason"] == "permission_surface_change"
    assert entry["sha"] == "abc123"
    assert entry["paths"] == [".github/workflows/ci.yml"]
    assert "created_at" in entry


def test_persist_override_merge(temp_state_dir) -> None:
    """persist_override merges with existing entries."""
    persist_override("a/b", "sha1", ["x"])
    persist_override("c/d", "sha2", ["y"])
    path = temp_state_dir / "security_overrides.json"
    with open(path) as f:
        data = json.load(f)
    assert "a/b:sha1" in data
    assert "c/d:sha2" in data
    assert data["a/b:sha1"]["paths"] == ["x"]
    assert data["c/d:sha2"]["paths"] == ["y"]
