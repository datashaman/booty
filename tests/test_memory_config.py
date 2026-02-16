"""Tests for MemoryConfig and BootyConfigV1.memory."""

import os

import pytest

from booty.memory.config import MemoryConfig, apply_memory_env_overrides
from booty.test_runner.config import BootyConfigV1, load_booty_config_from_content


def test_memory_config_accepts_valid_config():
    """MemoryConfig accepts valid config (enabled, retention_days, max_matches, comment_on_pr, comment_on_incident_issue)."""
    c = MemoryConfig(
        enabled=True,
        retention_days=90,
        max_matches=3,
        comment_on_pr=True,
        comment_on_incident_issue=True,
    )
    assert c.enabled is True
    assert c.retention_days == 90
    assert c.max_matches == 3
    assert c.comment_on_pr is True
    assert c.comment_on_incident_issue is True


def test_memory_config_rejects_unknown_keys():
    """MemoryConfig rejects unknown keys (extra='forbid')."""
    with pytest.raises(Exception):
        MemoryConfig(enabled=True, typo_key=1)


def test_booty_config_v1_with_valid_memory_block_loads_dict():
    """BootyConfigV1 with valid memory block loads with memory dict."""
    c = load_booty_config_from_content(
        "schema_version: 1\ntest_command: pytest\nmemory:\n  enabled: true\n  retention_days: 90"
    )
    assert c.memory is not None
    assert c.memory.get("enabled") is True
    assert c.memory.get("retention_days") == 90


def test_booty_config_v1_without_memory_key_loads_none():
    """BootyConfigV1 without memory key loads with memory=None."""
    c = load_booty_config_from_content("schema_version: 1\ntest_command: pytest")
    assert c.memory is None


def test_apply_memory_env_overrides():
    """apply_memory_env_overrides applies MEMORY_ENABLED, MEMORY_RETENTION_DAYS, MEMORY_MAX_MATCHES."""
    c = MemoryConfig(enabled=True, retention_days=90, max_matches=3)

    # Test MEMORY_ENABLED
    os.environ["MEMORY_ENABLED"] = "false"
    try:
        c2 = apply_memory_env_overrides(c)
        assert c2.enabled is False
    finally:
        os.environ.pop("MEMORY_ENABLED", None)

    # Test MEMORY_RETENTION_DAYS
    os.environ["MEMORY_RETENTION_DAYS"] = "30"
    try:
        c3 = apply_memory_env_overrides(c)
        assert c3.retention_days == 30
    finally:
        os.environ.pop("MEMORY_RETENTION_DAYS", None)

    # Test MEMORY_MAX_MATCHES
    os.environ["MEMORY_MAX_MATCHES"] = "5"
    try:
        c4 = apply_memory_env_overrides(c)
        assert c4.max_matches == 5
    finally:
        os.environ.pop("MEMORY_MAX_MATCHES", None)
