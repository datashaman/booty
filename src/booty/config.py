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
    TRIGGER_LABEL: str = "agent"
    GITHUB_TOKEN: str  # Required for cloning, pushing, and opening PRs

    # LLM configuration
    LLM_TIMEOUT: int = 300
    LLM_MAX_CONTEXT_TOKENS: int = 180000  # Context window budget, conservative buffer

    # Worker configuration
    MAX_RETRY_ATTEMPTS: int = 3
    WORKER_COUNT: int = 3
    QUEUE_MAX_SIZE: int = 100

    # Logging configuration
    LOG_LEVEL: str = "INFO"

    # Code generation limits
    MAX_FILES_PER_ISSUE: int = 10  # File count cap
    RESTRICTED_PATHS: str = ".github/workflows/**,.env,.env.*,**/*.env,**/secrets.*,Dockerfile,docker-compose*.yml,*lock.json,*.lock,.booty.yml"  # Comma-separated denylist patterns

    # Git commit attribution (Builder agent commits)
    BOOTY_GIT_AUTHOR_NAME: str = "Booty Agent"
    BOOTY_GIT_AUTHOR_EMAIL: str = "noreply@booty.dev"

    # Self-modification configuration
    BOOTY_OWN_REPO_URL: str = ""  # Empty means self-modification detection disabled
    BOOTY_SELF_MODIFY_ENABLED: bool = False  # Explicit opt-in required
    BOOTY_SELF_MODIFY_REVIEWER: str = ""  # GitHub username for review requests on self-PRs

    # Sentry error tracking
    SENTRY_DSN: str = ""  # Empty = not configured
    SENTRY_RELEASE: str = ""  # Optional; deploy sets from git rev-parse
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_SAMPLE_RATE: float = 1.0

    # Observability agent (Sentry webhook)
    SENTRY_WEBHOOK_SECRET: str = ""  # Optional; empty = webhook verification disabled (dev only)
    OBSV_MIN_SEVERITY: str = "error"  # fatal, error, warning, info, debug — default error and above
    OBSV_COOLDOWN_HOURS: float = 6.0
    
    # Internal test endpoints
    INTERNAL_TEST_TOKEN: str = ""  # Optional; empty = test endpoints open in development

    # Verifier (GitHub App) configuration
    GITHUB_APP_ID: str = ""  # Optional; empty = Verifier disabled
    GITHUB_APP_PRIVATE_KEY: str = ""  # Optional; empty = Verifier disabled
    VERIFIER_WORKER_COUNT: int = 2  # Number of verifier workers
    MAX_VERIFIER_RETRIES: int = 1  # Max verifier-triggered builder retries (prevents infinite loops)

    # Security (GitHub App) configuration — uses same App as Verifier
    SECURITY_WORKER_COUNT: int = 2  # Number of security workers

    # Reviewer (GitHub App) configuration — uses same App as Verifier
    REVIEWER_WORKER_COUNT: int = 2  # Number of reviewer workers

    # Planner agent — set to false to disable agent-triggered handling
    PLANNER_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


def verifier_enabled(settings: Settings) -> bool:
    """Return True if GitHub App credentials are configured for Verifier."""
    return bool(settings.GITHUB_APP_ID and settings.GITHUB_APP_PRIVATE_KEY)


def security_enabled(settings: Settings) -> bool:
    """Return True if GitHub App credentials are configured for Security (same App as Verifier)."""
    return bool(settings.GITHUB_APP_ID and settings.GITHUB_APP_PRIVATE_KEY)


def planner_enabled(settings: Settings) -> bool:
    """Return True if Planner agent is enabled (PLANNER_ENABLED env / Settings)."""
    return bool(settings.PLANNER_ENABLED)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
