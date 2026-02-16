"""Configuration schema and loading for .booty.yml files."""

from pathlib import Path
from typing import Literal

import os
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from booty.logging import get_logger

logger = get_logger()


BOOTY_CONFIG_PROTECTED_PATHS_DEFAULT = [
    ".github/workflows/**",
    ".env",
    ".env.*",
    "**/*.env",
    "**/secrets.*",
    "Dockerfile",
    "docker-compose*.yml",
]


class BootyConfig(BaseModel):
    """Schema for .booty.yml configuration file (schema_version 0 or absent)."""

    schema_version: int = Field(default=0, description="Schema version; 0 or absent = v0")
    test_command: str = Field(
        ...,
        description="Shell command to run tests (e.g., 'pytest tests/')",
    )

    timeout: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Maximum test execution time in seconds",
    )

    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of refinement attempts before giving up",
    )

    protected_paths: list[str] = Field(
        default_factory=lambda: list(BOOTY_CONFIG_PROTECTED_PATHS_DEFAULT),
        description="Paths protected from self-modification",
    )

    @field_validator("test_command")
    @classmethod
    def validate_command_not_empty(cls, v: str) -> str:
        """Ensure test command is not empty or whitespace."""
        if not v.strip():
            raise ValueError("test_command cannot be empty")
        return v.strip()

    @field_validator("protected_paths")
    @classmethod
    def validate_protected_paths_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure protected_paths always has minimum defaults."""
        if not v:
            return [".github/workflows/**", ".env", ".env.*"]
        return v


class ReleaseGovernorConfig(BaseModel):
    """Release Governor config block — env vars RELEASE_GOVERNOR_* override.
    unknown keys fail (model_config extra='forbid').
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    production_environment_name: str = "production"
    require_approval_for_first_deploy: bool = False
    high_risk_paths: list[str] = Field(
        default_factory=lambda: [".github/workflows/**", "**/migrations/**"],
        description="Pathspecs for HIGH risk",
    )
    migration_paths: list[str] = Field(
        default_factory=list,
        description="Pathspecs for migrations",
    )
    deploy_workflow_name: str = "deploy.yml"
    deploy_workflow_ref: str = "main"
    cooldown_minutes: int = Field(default=30, ge=0)
    max_deploys_per_hour: int = Field(default=6, ge=1)
    approval_mode: Literal["environment", "label", "comment"] = "environment"
    approval_label: str | None = None
    approval_command: str | None = None


def apply_release_governor_env_overrides(
    config: ReleaseGovernorConfig,
) -> ReleaseGovernorConfig:
    """Apply RELEASE_GOVERNOR_* env vars over config. Returns new config."""
    overrides: dict = {}
    if (v := os.environ.get("RELEASE_GOVERNOR_ENABLED")) is not None:
        overrides["enabled"] = v.lower() in ("1", "true", "yes")
    if (v := os.environ.get("RELEASE_GOVERNOR_COOLDOWN_MINUTES")) is not None:
        try:
            overrides["cooldown_minutes"] = int(v)
        except ValueError:
            pass
    if (v := os.environ.get("RELEASE_GOVERNOR_MAX_DEPLOYS_PER_HOUR")) is not None:
        try:
            overrides["max_deploys_per_hour"] = int(v)
        except ValueError:
            pass
    if (v := os.environ.get("RELEASE_GOVERNOR_DEPLOY_WORKFLOW_NAME")) is not None:
        overrides["deploy_workflow_name"] = v
    if (v := os.environ.get("RELEASE_GOVERNOR_PRODUCTION_ENVIRONMENT_NAME")) is not None:
        overrides["production_environment_name"] = v
    if (v := os.environ.get("RELEASE_GOVERNOR_REQUIRE_APPROVAL_FOR_FIRST_DEPLOY")) is not None:
        overrides["require_approval_for_first_deploy"] = v.lower() in ("1", "true", "yes")
    if (v := os.environ.get("RELEASE_GOVERNOR_APPROVAL_MODE")) is not None:
        if v in ("environment", "label", "comment"):
            overrides["approval_mode"] = v
    if (v := os.environ.get("RELEASE_GOVERNOR_APPROVAL_LABEL")) is not None:
        overrides["approval_label"] = v if v else None
    if (v := os.environ.get("RELEASE_GOVERNOR_APPROVAL_COMMAND")) is not None:
        overrides["approval_command"] = v if v else None

    if not overrides:
        return config
    return config.model_copy(update=overrides)


class BootyConfigV1(BaseModel):
    """Strict schema v1 — unknown keys fail validation."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    test_command: str = Field(
        ...,
        description="Shell command to run tests (e.g., 'pytest tests/')",
    )
    setup_command: str | None = Field(default=None, description="Optional setup command")
    install_command: str | None = Field(
        default=None,
        description="Command to install deps (e.g. 'pip install -r requirements.txt'). Required for agent PRs when import validation runs.",
    )
    timeout_seconds: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Maximum test execution time in seconds",
    )
    max_retries: int = Field(default=3, ge=1, le=10)
    allowed_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    allowed_commands: list[str] = Field(default_factory=list)
    network_policy: (
        Literal["deny_all", "registry_only", "allow_list"] | None
    ) = None
    labels: dict[str, str] = Field(default_factory=dict)
    max_files_changed: int | None = None
    max_diff_loc: int | None = None
    max_loc_per_file: int | None = None
    max_loc_per_file_pathspec: list[str] | None = None
    protected_paths: list[str] = Field(
        default_factory=lambda: list(BOOTY_CONFIG_PROTECTED_PATHS_DEFAULT),
    )
    release_governor: ReleaseGovernorConfig | None = Field(
        default=None,
        description="Optional release governor config",
    )

    @property
    def timeout(self) -> int:
        """Executor compatibility: expose timeout_seconds as .timeout."""
        return self.timeout_seconds

    @field_validator("test_command")
    @classmethod
    def validate_command_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("test_command cannot be empty")
        return v.strip()


def _parse_booty_config(data: dict) -> BootyConfig | BootyConfigV1:
    """Parse and validate config dict; dispatch by schema_version."""
    if data.get("schema_version") == 1:
        return BootyConfigV1.model_validate(data)
    return BootyConfig.model_validate(data)


def load_booty_config(workspace_path: Path) -> BootyConfig | BootyConfigV1:
    """Load and validate .booty.yml from workspace root.

    Args:
        workspace_path: Path to workspace root directory

    Returns:
        Validated BootyConfig or BootyConfigV1. If .booty.yml doesn't exist,
        returns default config with echo command.

    Raises:
        yaml.YAMLError: If YAML is malformed
        ValidationError: If config schema is invalid
    """
    config_path = workspace_path / ".booty.yml"

    if not config_path.exists():
        logger.info(
            "No .booty.yml found, using default config",
            workspace_path=str(workspace_path),
        )
        return BootyConfig(test_command="echo 'No tests configured'")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(".booty.yml is empty")

    return _parse_booty_config(data)


def load_booty_config_from_content(yaml_content: str) -> BootyConfig | BootyConfigV1:
    """Load and validate config from YAML string (e.g. API-fetched .booty.yml).

    Args:
        yaml_content: Raw YAML string

    Returns:
        Validated BootyConfig or BootyConfigV1

    Raises:
        ValueError: If content is empty
        yaml.YAMLError: If YAML is malformed
        ValidationError: If config schema is invalid (v1 rejects unknown keys)
    """
    content = yaml_content.strip() if yaml_content else ""
    if not content:
        raise ValueError(".booty.yml is empty")

    data = yaml.safe_load(content)
    if data is None:
        raise ValueError(".booty.yml is empty")

    return _parse_booty_config(data)
