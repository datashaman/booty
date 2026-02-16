"""Tests for planner config."""

import os

import pytest

from booty.planner.config import PlannerConfig, apply_planner_env_overrides
from booty.test_runner.config import load_booty_config_from_content


def test_planner_config_default_enabled_true() -> None:
    """PlannerConfig default enabled=True."""
    c = PlannerConfig()
    assert c.enabled is True


def test_booty_config_v1_loads_planner_block() -> None:
    """BootyConfigV1 loads planner block."""
    c = load_booty_config_from_content(
        "schema_version: 1\ntest_command: pytest\nplanner:\n  enabled: true"
    )
    assert c.planner is not None
    assert c.planner.enabled is True


def test_invalid_planner_block_sets_none() -> None:
    """Invalid planner block sets planner=None."""
    c = load_booty_config_from_content(
        "schema_version: 1\ntest_command: pytest\nplanner:\n  enabled: not_a_bool"
    )
    assert c.planner is None


def test_apply_planner_env_overrides_planner_enabled_false() -> None:
    """apply_planner_env_overrides with PLANNER_ENABLED=false."""
    os.environ["PLANNER_ENABLED"] = "false"
    try:
        c = PlannerConfig(enabled=True)
        c2 = apply_planner_env_overrides(c)
        assert c2.enabled is False
    finally:
        os.environ.pop("PLANNER_ENABLED", None)


def test_apply_planner_env_overrides_no_env_unchanged() -> None:
    """apply_planner_env_overrides with no env leaves config unchanged."""
    os.environ.pop("PLANNER_ENABLED", None)  # ensure not set
    c = PlannerConfig(enabled=True)
    c2 = apply_planner_env_overrides(c)
    assert c2.enabled is True
    assert c2 is c  # same object when no overrides
