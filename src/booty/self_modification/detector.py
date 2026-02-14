"""Self-modification detection via URL comparison."""

import giturlparse

from booty.logging import get_logger

logger = get_logger()


def is_self_modification(webhook_repo_url: str, booty_own_repo_url: str) -> bool:
    """
    Detect if webhook target matches Booty's own repository.

    Args:
        webhook_repo_url: Repository URL from webhook payload
        booty_own_repo_url: Configured URL of Booty's own repository

    Returns:
        True if URLs reference the same repository (same host/owner/repo),
        False if different repositories or if detection disabled (empty booty_own_repo_url)

    Comparison normalizes across HTTPS/SSH/case/.git variants.
    """
    # Detection disabled if booty_own_repo_url is empty
    if not booty_own_repo_url:
        logger.debug("Self-modification detection disabled (BOOTY_OWN_REPO_URL empty)")
        return False

    # Parse both URLs
    webhook_parsed = giturlparse.parse(webhook_repo_url)
    booty_parsed = giturlparse.parse(booty_own_repo_url)

    # Validate both URLs
    if not giturlparse.validate(webhook_repo_url):
        logger.warning(
            "Invalid webhook repository URL",
            webhook_repo_url=webhook_repo_url,
        )
        return False

    if not giturlparse.validate(booty_own_repo_url):
        logger.warning(
            "Invalid Booty repository URL",
            booty_own_repo_url=booty_own_repo_url,
        )
        return False

    # Compare host, owner, and repo (all lowercased to handle case variations)
    # All three must match to prevent fork false positives
    host_match = webhook_parsed.host.lower() == booty_parsed.host.lower()
    owner_match = webhook_parsed.owner.lower() == booty_parsed.owner.lower()
    repo_match = webhook_parsed.repo.lower() == booty_parsed.repo.lower()

    is_match = host_match and owner_match and repo_match

    logger.debug(
        "Self-modification detection result",
        webhook_owner=webhook_parsed.owner,
        webhook_repo=webhook_parsed.repo,
        booty_owner=booty_parsed.owner,
        booty_repo=booty_parsed.repo,
        is_self_modification=is_match,
    )

    return is_match
