"""Structured logging configuration for Booty."""

import logging

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structlog for JSON logging with correlation IDs.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to reduce library noise
    logging.basicConfig(
        format="%(message)s",
        level=logging.WARNING,
    )

    # Set our log level
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))


def get_logger() -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance."""
    return structlog.get_logger()
