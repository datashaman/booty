"""Tests for ReleaseGovernorConfig and env override support."""

import os

import pytest
from pydantic import ValidationError

from booty.test_runner.config import (
    apply_release_governor_env_overrides,
    load_booty_config_from_content,
)


def test_valid_release_governor_loads() -> None:
    """Valid release_governor config loads."""
    c = load_booty_config_from_content(
        "schema_version: 1\ntest_command: pytest\nrelease_governor:\n  enabled: true"
    )
    assert c.release_governor is not None
    assert c.release_governor.enabled is True


def test_unknown_key_raises_validation_error() -> None:
    """Unknown key in release_governor raises ValidationError (extra='forbid')."""
    with pytest.raises(ValidationError):
        load_booty_config_from_content(
            "schema_version: 1\ntest_command: pytest\nrelease_governor:\n  enabled: true\n  unknown_key: x"
        )


def test_without_release_governor_loads() -> None:
    """BootyConfigV1 without release_governor loads (release_governor is None)."""
    c = load_booty_config_from_content("schema_version: 1\ntest_command: pytest")
    assert c.release_governor is None


def test_env_overrides_enabled_and_cooldown() -> None:
    """apply_release_governor_env_overrides overrides enabled, cooldown_minutes from env."""
    os.environ["RELEASE_GOVERNOR_ENABLED"] = "false"
    try:
        c = load_booty_config_from_content(
            "schema_version: 1\ntest_command: pytest\nrelease_governor:\n  enabled: true"
        )
        assert c.release_governor is not None
        r = apply_release_governor_env_overrides(c.release_governor)
        assert r.enabled is False
    finally:
        os.environ.pop("RELEASE_GOVERNOR_ENABLED", None)

    os.environ["RELEASE_GOVERNOR_COOLDOWN_MINUTES"] = "60"
    try:
        c = load_booty_config_from_content(
            "schema_version: 1\ntest_command: pytest\nrelease_governor:\n  enabled: true"
        )
        assert c.release_governor is not None
        r = apply_release_governor_env_overrides(c.release_governor)
        assert r.cooldown_minutes == 60
    finally:
        os.environ.pop("RELEASE_GOVERNOR_COOLDOWN_MINUTES", None)


def test_invalid_approval_mode_raises_validation_error() -> None:
    """Invalid approval_mode value raises ValidationError."""
    with pytest.raises(ValidationError):
        load_booty_config_from_content(
            "schema_version: 1\ntest_command: pytest\nrelease_governor:\n  approval_mode: invalid"
        )
