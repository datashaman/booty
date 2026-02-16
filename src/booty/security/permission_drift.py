"""Permission drift detection — sensitive path changes trigger ESCALATE."""

from __future__ import annotations

from pathspec import PathSpec


def get_changed_paths(repo, base_sha: str, head_sha: str) -> list[tuple[str, str | None]]:
    """Return list of (path, old_path_or_none) from diff.

    For renames (R), old_path is the first path, path is the second.
    Uses git diff --name-status -z for NUL-separated output.
    """
    try:
        out = repo.git.diff(
            "--name-status",
            "-z",
            "--find-renames",
            base_sha,
            head_sha,
        )
    except Exception:
        return []

    if not out.strip():
        return []

    result: list[tuple[str, str | None]] = []
    parts = out.split("\x00")
    i = 0
    while i < len(parts):
        status = parts[i].strip() if i < len(parts) else ""
        i += 1
        if not status or i >= len(parts):
            continue
        path = parts[i].strip()
        i += 1

        old_path: str | None = None
        if status.startswith("R") and i < len(parts):
            # Rename: status R, old_path, new_path (path was old_path)
            old_path = path
            path = parts[i].strip()
            i += 1

        result.append((path, old_path))
    return result


def sensitive_paths_touched(
    paths: list[tuple[str, str | None]],
    sensitive_paths: list[str],
) -> list[str]:
    """Return deduplicated list of sensitive paths that were touched.

    For renames, matches both old and new path against sensitive_paths.
    """
    if not sensitive_paths:
        return []
    spec = PathSpec.from_lines("gitwildmatch", sensitive_paths)
    touched: set[str] = set()
    for path, old_path in paths:
        if spec.match_file(path):
            touched.add(path)
        if old_path and spec.match_file(old_path):
            touched.add(old_path)
    return sorted(touched)


_PATH_CATEGORIES: list[tuple[str, str]] = [
    (".github/workflows/", "workflow modified"),
    ("infra/", "infra modified"),
    ("terraform/", "terraform modified"),
    ("helm/", "helm modified"),
    ("k8s/", "k8s modified"),
    ("iam/", "iam modified"),
    ("auth/", "auth modified"),
    ("security/", "security modified"),
]


def _title_for_paths(paths: list[str]) -> str:
    """Map path prefix to escalation category for title."""
    if not paths:
        return "Security escalated — permission surface changed"
    first = paths[0]
    for prefix, category in _PATH_CATEGORIES:
        if first.startswith(prefix):
            return f"Security escalated — {category}"
    return "Security escalated — permission surface changed"
