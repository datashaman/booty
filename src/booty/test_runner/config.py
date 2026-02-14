"""Configuration schema and loading for .booty.yml files."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from booty.logging import get_logger

logger = get_logger()


class BootyConfig(BaseModel):
    """Schema for .booty.yml configuration file."""

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
        default_factory=lambda: [
            ".github/workflows/**",
            ".env",
            ".env.*",
            "**/*.env",
            "**/secrets.*",
            "Dockerfile",
            "docker-compose*.yml",
        ],
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


def load_booty_config(workspace_path: Path) -> BootyConfig:
    """Load and validate .booty.yml from workspace root.

    Args:
        workspace_path: Path to workspace root directory

    Returns:
        Validated BootyConfig instance. If .booty.yml doesn't exist, returns
        default config with echo command (allows self-modification on repos
        without tests).

    Raises:
        yaml.YAMLError: If YAML is malformed
        ValidationError: If config schema is invalid
    """
    config_path = workspace_path / ".booty.yml"

    if not config_path.exists():
        # Return default config instead of raising error
        # This allows self-modification to work on repos without .booty.yml
        logger.info(
            "No .booty.yml found, using default config",
            workspace_path=str(workspace_path),
        )
        return BootyConfig(test_command="echo 'No tests configured'")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(".booty.yml is empty")

    return BootyConfig.model_validate(data)
