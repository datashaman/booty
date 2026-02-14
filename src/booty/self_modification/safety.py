"""Protected path validation for self-modification safety."""

from pathlib import Path

from booty.code_gen.security import PathRestrictor
from booty.logging import get_logger
from booty.test_runner.config import load_booty_config

logger = get_logger()


def create_self_modification_restrictor(workspace_path: Path) -> PathRestrictor:
    """
    Create PathRestrictor with protected paths from .booty.yml.

    Args:
        workspace_path: Path to workspace root

    Returns:
        PathRestrictor configured with protected_paths from config
    """
    config = load_booty_config(workspace_path)
    restrictor = PathRestrictor(
        workspace_root=workspace_path,
        denylist_patterns=config.protected_paths,
    )

    logger.info(
        "Created self-modification restrictor",
        protected_paths_count=len(config.protected_paths),
    )

    return restrictor


def validate_changes_against_protected_paths(
    changes: list[dict], workspace_path: Path
) -> tuple[bool, str | None]:
    """
    Validate file changes against protected path patterns.

    Args:
        changes: List of change dicts with "path" key
        workspace_path: Path to workspace root

    Returns:
        (True, None) if all paths allowed
        (False, reason) if any path violates protected patterns
    """
    restrictor = create_self_modification_restrictor(workspace_path)

    for change in changes:
        file_path = change.get("path")
        if not file_path:
            continue

        allowed, reason = restrictor.is_path_allowed(file_path)
        if not allowed:
            logger.warning(
                "Protected path violation detected",
                file_path=file_path,
                reason=reason,
            )
            return False, reason

    return True, None
