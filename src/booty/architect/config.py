"""Architect config schema and env overrides."""

import os

from pydantic import BaseModel, ConfigDict, ValidationError


class ArchitectConfigError(Exception):
    """Raised when architect block has invalid or unknown keys.

    Validation happens at get_architect_config, not at BootyConfig load.
    """

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


class ArchitectConfig(BaseModel):
    """Architect config block — enabled, rewrite_ambiguous_steps, enforce_risk_rules.

    Unknown keys fail (model_config extra='forbid').
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    builder_compat: bool = True
    rewrite_ambiguous_steps: bool = True
    enforce_risk_rules: bool = True


def get_architect_config(booty_config: object) -> ArchitectConfig | None:
    """Validate booty_config.architect into ArchitectConfig.

    Returns None if architect is None or absent.
    Raises ArchitectConfigError when architect block has unknown/invalid keys.
    """
    architect = getattr(booty_config, "architect", None)
    if architect is None:
        return None
    if not isinstance(architect, dict):
        return None
    try:
        return ArchitectConfig.model_validate(architect)
    except ValidationError as e:
        raise ArchitectConfigError(
            f"Invalid architect config in .booty.yml: {e!s}",
            cause=e,
        ) from e


def apply_architect_env_overrides(config: ArchitectConfig) -> ArchitectConfig:
    """Apply ARCHITECT_ENABLED and ARCHITECT_BUILDER_COMPAT env vars. Returns new config."""
    v = os.environ.get("ARCHITECT_ENABLED")
    if v is not None:
        low = v.lower()
        enabled = low in ("1", "true", "yes")
        if low in ("0", "false", "no"):
            enabled = False
        if low in ("1", "true", "yes", "0", "false", "no"):
            config = config.model_copy(update={"enabled": enabled})

    v = os.environ.get("ARCHITECT_BUILDER_COMPAT")
    if v is not None:
        low = v.lower()
        builder_compat = low in ("1", "true", "yes")
        if low in ("0", "false", "no"):
            builder_compat = False
        if low in ("1", "true", "yes", "0", "false", "no"):
            config = config.model_copy(update={"builder_compat": builder_compat})

    return config
