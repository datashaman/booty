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

    # Phase 2: LLM Code Generation
    ANTHROPIC_API_KEY: str  # Required, no default
    LLM_MAX_TOKENS: int = 4096  # Max output tokens for generation
    LLM_MAX_CONTEXT_TOKENS: int = 180000  # Context window budget, conservative buffer
    MAX_FILES_PER_ISSUE: int = 10  # File count cap
    RESTRICTED_PATHS: str = ".github/workflows/**,.env,.env.*,**/*.env,**/secrets.*,Dockerfile,docker-compose*.yml,*lock.json,*.lock"  # Comma-separated denylist patterns

    # Phase 4: Self-modification configuration
    BOOTY_OWN_REPO_URL: str = ""  # Empty means self-modification detection disabled
    BOOTY_SELF_MODIFY_ENABLED: bool = False  # Explicit opt-in required
    BOOTY_SELF_MODIFY_REVIEWER: str = ""  # GitHub username for review requests on self-PRs

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
