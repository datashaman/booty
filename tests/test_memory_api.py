"""Tests for memory.add_record API and get_memory_config."""

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from booty.memory import MemoryConfig, add_record, get_memory_config


def test_add_record_when_disabled_returns_success_no_persist(monkeypatch, tmp_path):
    """add_record when disabled returns success, no persist."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    config = MemoryConfig(enabled=False)
    result = add_record({"type": "test", "repo": "x/y"}, config)
    assert result["added"] is True
    assert result["id"] is None
    path = tmp_path / "memory.jsonl"
    assert not path.exists()


def test_add_record_when_enabled_persists_and_returns_id(monkeypatch, tmp_path):
    """add_record when enabled persists and returns id."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    config = MemoryConfig(enabled=True)
    result = add_record({"type": "test", "repo": "x/y"}, config)
    assert result["added"] is True
    assert result["id"] is not None
    path = tmp_path / "memory.jsonl"
    assert path.exists()
    content = path.read_text()
    assert "test" in content
    assert result["id"] in content


def test_add_record_dedup_same_key_within_24h_returns_duplicate(monkeypatch, tmp_path):
    """add_record dedup: same key within 24h returns duplicate."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    config = MemoryConfig(enabled=True)
    r1 = add_record({"type": "incident", "repo": "o/r", "sha": "abc"}, config)
    assert r1["added"] is True
    r2 = add_record({"type": "incident", "repo": "o/r", "sha": "abc"}, config)
    assert r2["added"] is False
    assert r2["reason"] == "duplicate"
    assert r2["existing_id"] == r1["id"]


def test_add_record_excludes_null_empty_from_dedup_key(monkeypatch, tmp_path):
    """add_record excludes null/empty from dedup key — records with/without fingerprint differentiated."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    config = MemoryConfig(enabled=True)
    # Record without fingerprint
    r1 = add_record({"type": "incident", "repo": "o/r", "sha": "abc"}, config)
    assert r1["added"] is True
    # Record with same type/repo/sha but different fingerprint — should NOT dedup (fingerprint in key)
    r2 = add_record({"type": "incident", "repo": "o/r", "sha": "abc", "fingerprint": "fp1"}, config)
    assert r2["added"] is True  # different key because fingerprint differs
    # Same fingerprint — should dedup
    r3 = add_record({"type": "incident", "repo": "o/r", "sha": "abc", "fingerprint": "fp1"}, config)
    assert r3["added"] is False
    assert r3["reason"] == "duplicate"


def test_get_memory_config_raises_on_unknown_key():
    """get_memory_config raises on unknown key."""
    c = SimpleNamespace(memory={"enabled": True, "typo_key": 1})
    with pytest.raises(Exception) as exc_info:
        get_memory_config(c)
    assert "typo_key" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()


def test_get_memory_config_returns_none_when_memory_none():
    """get_memory_config returns None when memory is None."""
    c = SimpleNamespace(memory=None)
    assert get_memory_config(c) is None


def test_get_memory_config_returns_config_when_valid():
    """get_memory_config returns MemoryConfig when valid."""
    c = SimpleNamespace(memory={"enabled": True, "retention_days": 90})
    mc = get_memory_config(c)
    assert mc is not None
    assert mc.enabled is True
    assert mc.retention_days == 90
