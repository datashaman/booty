"""Path security and restriction enforcement for LLM-generated file operations.

This module provides the PathRestrictor class which enforces workspace boundaries
and denylist patterns to prevent LLM-generated code from touching sensitive files
like CI configs, secrets, and deployment manifests.
"""

from pathlib import Path
import pathspec


class PathRestrictor:
    """Enforce path restrictions with workspace containment and denylist patterns.

    Uses canonical path resolution (pathlib.resolve()) to prevent path traversal
    attacks and pathspec for gitignore-style pattern matching.
    """

    def __init__(self, workspace_root: Path, denylist_patterns: list[str]):
        """Initialize path restrictor with workspace root and denylist patterns.

        Args:
            workspace_root: Root directory of the workspace (will be resolved to canonical path)
            denylist_patterns: List of gitignore-style patterns (supports ** for recursive matching)
        """
        self.workspace_root = workspace_root.resolve()
        # Use pathspec for gitignore-style patterns (supports **)
        self.denylist = pathspec.PathSpec.from_lines('gitwildmatch', denylist_patterns)

    def is_path_allowed(self, file_path: str) -> tuple[bool, str | None]:
        """Validate path against security restrictions.

        Checks:
        1. Path must resolve to a location within workspace_root (prevent traversal)
        2. Path must not match any denylist patterns

        Args:
            file_path: Relative path from workspace root to validate

        Returns:
            Tuple of (allowed: bool, reason: str | None)
            - (True, None) if path is allowed
            - (False, reason) if path is denied with explanation
        """
        # Resolve to absolute canonical path (follows symlinks, resolves ..)
        try:
            resolved_path = (self.workspace_root / file_path).resolve()
        except (OSError, RuntimeError) as e:
            # Path resolution can fail for various reasons (symlink loops, permission errors, etc.)
            return False, f"Path resolution failed: {e}"

        # Check 1: Must be within workspace (prevent path traversal like ../../etc/passwd)
        try:
            if not resolved_path.is_relative_to(self.workspace_root):
                return False, f"Path escapes workspace: {file_path}"
        except ValueError:
            # is_relative_to can raise ValueError in edge cases
            return False, f"Path escapes workspace: {file_path}"

        # Check 2: Must not match denylist patterns
        relative_path = resolved_path.relative_to(self.workspace_root)
        if self.denylist.match_file(str(relative_path)):
            return False, f"Path matches restricted pattern: {file_path}"

        return True, None

    @classmethod
    def from_config(cls, workspace_root: Path, restricted_paths_csv: str) -> "PathRestrictor":
        """Create PathRestrictor from CSV string of denylist patterns.

        Args:
            workspace_root: Root directory of the workspace
            restricted_paths_csv: Comma-separated string of gitignore-style patterns

        Returns:
            PathRestrictor instance configured with parsed patterns
        """
        patterns = [p.strip() for p in restricted_paths_csv.split(',') if p.strip()]
        return cls(workspace_root, patterns)

    def validate_all_paths(self, file_paths: list[str]) -> None:
        """Validate multiple paths, raising ValueError on first violation.

        Args:
            file_paths: List of relative paths to validate

        Raises:
            ValueError: If any path is denied, with details on which path and why
        """
        for file_path in file_paths:
            allowed, reason = self.is_path_allowed(file_path)
            if not allowed:
                raise ValueError(f"Path validation failed: {reason}")
