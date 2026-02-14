"""Configuration management for Booty."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Webhook configuration
    WEBHOOK_SECRET: str  # Required, no default

    # Repository configuration
    TARGET_REPO_URL: str  # Required, no default
    TARGET_BRANCH: str = "main"
    TRIGGER_LABEL: str = "agent:builder"
    GITHUB_TOKEN: str = ""  # Optional, for private repos

    # LLM configuration (REQ-17: deterministic by default)
    LLM_TEMPERATURE: float = 0.0
    LLM_MODEL: str = "claude-sonnet-4"
    LLM_TIMEOUT: int = 300

    # Worker configuration
    MAX_RETRY_ATTEMPTS: int = 3
    WORKER_COUNT: int = 3
    QUEUE_MAX_SIZE: int = 100

    # Logging configuration
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
