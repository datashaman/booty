"""Memory config schema and env overrides."""

import os
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class MemoryConfigError(Exception):
    """Raised when memory config is invalid (e.g. unknown keys)."""


class MemoryConfig(BaseModel):
    """Memory config block — enabled, retention_days, max_matches, comment_on_pr, comment_on_incident_issue.
    Unknown keys fail (model_config extra='forbid').
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    retention_days: int = Field(default=90, ge=1, le=365)
    max_matches: int = Field(default=3, ge=1, le=20)
    comment_on_pr: bool = True
    comment_on_incident_issue: bool = True


def apply_memory_env_overrides(config: MemoryConfig) -> MemoryConfig:
    """Apply MEMORY_* env vars over config. Returns new config."""
    overrides: dict = {}
    if (v := os.environ.get("MEMORY_ENABLED")) is not None:
        low = v.lower()
        overrides["enabled"] = low in ("1", "true", "yes")
    if (v := os.environ.get("MEMORY_RETENTION_DAYS")) is not None:
        try:
            val = int(v)
            if 1 <= val <= 365:
                overrides["retention_days"] = val
        except ValueError:
            pass
    if (v := os.environ.get("MEMORY_MAX_MATCHES")) is not None:
        try:
            val = int(v)
            if 1 <= val <= 20:
                overrides["max_matches"] = val
        except ValueError:
            pass
    if not overrides:
        return config
    return config.model_copy(update=overrides)


def get_memory_config(booty_config: object) -> MemoryConfig | None:
    """Validate booty_config.memory into MemoryConfig. Returns None if memory is None."""
    memory = getattr(booty_config, "memory", None)
    if memory is None:
        return None
    try:
        return MemoryConfig.model_validate(memory)
    except ValidationError as e:
        raise MemoryConfigError(f"Memory config invalid: {e}") from e
