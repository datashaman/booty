"""Tests for architect config."""

import os

import pytest

from booty.architect.config import (
    ArchitectConfig,
    ArchitectConfigError,
    apply_architect_env_overrides,
    get_architect_config,
)
from booty.test_runner.config import load_booty_config_from_content


def test_architect_config_defaults() -> None:
    """ArchitectConfig has enabled, rewrite_ambiguous_steps, enforce_risk_rules defaults."""
    c = ArchitectConfig()
    assert c.enabled is True
    assert c.rewrite_ambiguous_steps is True
    assert c.enforce_risk_rules is True


def test_booty_config_v1_loads_architect_block_as_raw_dict() -> None:
    """BootyConfigV1 loads architect block as raw dict."""
    c = load_booty_config_from_content(
        "schema_version: 1\ntest_command: pytest\narchitect:\n  enabled: true\n"
        "  rewrite_ambiguous_steps: true\n  enforce_risk_rules: true"
    )
    assert c.architect is not None
    assert isinstance(c.architect, dict)
    assert c.architect.get("enabled") is True


def test_get_architect_config_returns_config_from_valid_block() -> None:
    """get_architect_config returns ArchitectConfig from valid block."""
    c = load_booty_config_from_content(
        "schema_version: 1\ntest_command: pytest\narchitect:\n  enabled: true\n"
        "  rewrite_ambiguous_steps: true\n  enforce_risk_rules: true"
    )
    ac = get_architect_config(c)
    assert ac is not None
    assert ac.enabled is True
    assert ac.rewrite_ambiguous_steps is True
    assert ac.enforce_risk_rules is True


def test_get_architect_config_returns_none_when_absent() -> None:
    """get_architect_config returns None when architect block absent."""
    c = load_booty_config_from_content("schema_version: 1\ntest_command: pytest")
    assert c.architect is None
    assert get_architect_config(c) is None


def test_get_architect_config_raises_on_unknown_key() -> None:
    """get_architect_config raises ArchitectConfigError when architect block has unknown key."""
    c = load_booty_config_from_content(
        "schema_version: 1\ntest_command: pytest\narchitect:\n  enabled: true\n  enabeled: true"
    )
    assert c.architect is not None
    with pytest.raises(ArchitectConfigError):
        get_architect_config(c)


def test_apply_architect_env_overrides_architect_enabled_false() -> None:
    """apply_architect_env_overrides with ARCHITECT_ENABLED=false."""
    os.environ["ARCHITECT_ENABLED"] = "false"
    try:
        c = ArchitectConfig(enabled=True)
        c2 = apply_architect_env_overrides(c)
        assert c2.enabled is False
    finally:
        os.environ.pop("ARCHITECT_ENABLED", None)


def test_apply_architect_env_overrides_no_env_unchanged() -> None:
    """apply_architect_env_overrides with no env leaves config unchanged."""
    os.environ.pop("ARCHITECT_ENABLED", None)
    c = ArchitectConfig(enabled=True)
    c2 = apply_architect_env_overrides(c)
    assert c2.enabled is True
    assert c2 is c
