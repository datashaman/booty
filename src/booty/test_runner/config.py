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

    @field_validator("test_command")
    @classmethod
    def validate_command_not_empty(cls, v: str) -> str:
        """Ensure test command is not empty or whitespace."""
        if not v.strip():
            raise ValueError("test_command cannot be empty")
        return v.strip()


def load_booty_config(workspace_path: Path) -> BootyConfig:
    """Load and validate .booty.yml from workspace root.

    Args:
        workspace_path: Path to workspace root directory

    Returns:
        Validated BootyConfig instance

    Raises:
        FileNotFoundError: If .booty.yml doesn't exist
        yaml.YAMLError: If YAML is malformed
        ValidationError: If config schema is invalid
    """
    config_path = workspace_path / ".booty.yml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"No .booty.yml configuration found in {workspace_path}. "
            "Test-driven refinement requires a .booty.yml file specifying "
            "how to run tests. Example:\n\n"
            "test_command: pytest tests/\n"
            "timeout: 300\n"
            "max_retries: 3\n"
        )

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(".booty.yml is empty")

    return BootyConfig.model_validate(data)
