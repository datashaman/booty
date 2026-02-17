"""Reviewer config schema and env overrides."""

import os

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ReviewerConfigError(Exception):
    """Raised when reviewer block has invalid or unknown keys.

    Validation happens at get_reviewer_config, not at BootyConfig load.
    """

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


class ReviewerConfig(BaseModel):
    """Reviewer config block — enabled, block_on.

    Unknown keys fail (model_config extra='forbid').
    block_on values map in Phase 39 (e.g. overengineering, poor_tests).
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    block_on: list[str] = Field(
        default_factory=list,
        description="Block-on categories (e.g. overengineering, poor_tests, duplication)",
    )


def get_reviewer_config(booty_config: object) -> ReviewerConfig | None:
    """Validate booty_config.reviewer into ReviewerConfig.

    Returns None if reviewer is None or absent.
    Raises ReviewerConfigError when reviewer block has unknown/invalid keys.
    """
    reviewer = getattr(booty_config, "reviewer", None)
    if reviewer is None:
        return None
    if not isinstance(reviewer, dict):
        return None
    try:
        return ReviewerConfig.model_validate(reviewer)
    except ValidationError as e:
        raise ReviewerConfigError(
            f"Invalid reviewer config in .booty.yml: {e!s}",
            cause=e,
        ) from e


def apply_reviewer_env_overrides(config: ReviewerConfig) -> ReviewerConfig:
    """Apply REVIEWER_ENABLED env var. Returns new config."""
    v = os.environ.get("REVIEWER_ENABLED")
    if v is None:
        return config
    low = v.lower()
    enabled = low in ("1", "true", "yes")
    if low in ("0", "false", "no"):
        enabled = False
    if low not in ("1", "true", "yes", "0", "false", "no"):
        return config
    return config.model_copy(update={"enabled": enabled})
