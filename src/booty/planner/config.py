"""Planner config schema and env overrides."""

import os

from pydantic import BaseModel, ConfigDict


class PlannerConfig(BaseModel):
    """Planner config block — enabled. Unknown keys fail (extra='forbid')."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True


def apply_planner_env_overrides(config: PlannerConfig) -> PlannerConfig:
    """Apply PLANNER_* env vars over config. Returns new config."""
    overrides: dict = {}
    if (v := os.environ.get("PLANNER_ENABLED")) is not None:
        low = v.lower()
        overrides["enabled"] = low in ("1", "true", "yes")
    if not overrides:
        return config
    return config.model_copy(update=overrides)


def get_planner_config(booty_config: object) -> PlannerConfig | None:
    """Validate booty_config.planner into PlannerConfig. Returns None if planner is None."""
    planner = getattr(booty_config, "planner", None)
    if planner is None:
        return None
    return PlannerConfig.model_validate(planner)
