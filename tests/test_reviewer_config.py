"""Tests for reviewer config."""

import os

import pytest

from booty.reviewer.config import (
    ReviewerConfig,
    ReviewerConfigError,
    apply_reviewer_env_overrides,
    get_reviewer_config,
)
from booty.test_runner.config import load_booty_config_from_content


def test_get_reviewer_config_returns_none_when_absent() -> None:
    """get_reviewer_config returns None when reviewer block absent."""
    c = load_booty_config_from_content("schema_version: 1\ntest_command: pytest")
    assert c.reviewer is None
    assert get_reviewer_config(c) is None


def test_get_reviewer_config_valid() -> None:
    """get_reviewer_config returns ReviewerConfig from valid block."""
    c = load_booty_config_from_content(
        "schema_version: 1\ntest_command: pytest\nreviewer:\n  enabled: true\n  block_on: [overengineering, poor_tests]"
    )
    rc = get_reviewer_config(c)
    assert rc is not None
    assert rc.enabled is True
    assert rc.block_on == ["overengineering", "poor_tests"]


def test_get_reviewer_config_unknown_key_raises() -> None:
    """get_reviewer_config raises ReviewerConfigError when reviewer block has unknown key."""
    c = load_booty_config_from_content(
        "schema_version: 1\ntest_command: pytest\nreviewer:\n  enabled: true\n  typo: bad"
    )
    assert c.reviewer is not None
    with pytest.raises(ReviewerConfigError):
        get_reviewer_config(c)


def test_apply_reviewer_env_overrides() -> None:
    """REVIEWER_ENABLED env overrides: 1/true/yes -> enabled True; 0/false/no -> False; unset -> unchanged."""
    try:
        os.environ["REVIEWER_ENABLED"] = "1"
        c = ReviewerConfig(enabled=False)
        c2 = apply_reviewer_env_overrides(c)
        assert c2.enabled is True

        os.environ["REVIEWER_ENABLED"] = "0"
        c3 = apply_reviewer_env_overrides(c2)
        assert c3.enabled is False

        os.environ.pop("REVIEWER_ENABLED", None)
        c4 = ReviewerConfig(enabled=True)
        c5 = apply_reviewer_env_overrides(c4)
        assert c5.enabled is True
        assert c5 is c4
    finally:
        os.environ.pop("REVIEWER_ENABLED", None)


def test_missing_block_disabled() -> None:
    """get_reviewer_config returns None when reviewer absent — caller treats as disabled."""
    c = load_booty_config_from_content("schema_version: 1\ntest_command: pytest")
    assert get_reviewer_config(c) is None


def test_booty_config_v1_loads_reviewer_block_as_raw_dict_with_unknown_keys() -> None:
    """BootyConfigV1 loads reviewer block as raw dict even with unknown keys."""
    c = load_booty_config_from_content(
        "schema_version: 1\ntest_command: pytest\nreviewer:\n  enabled: true\n  typo: bad"
    )
    assert hasattr(c, "reviewer")
    assert c.reviewer == {"enabled": True, "typo": "bad"}
