"""Planner risk classification from touch_paths — deterministic, rules-based."""

from typing import Literal

from pathspec import PathSpec

HIGH_RISK_PATTERNS = [
    ".github/workflows/**",
    "infra/**",
    "terraform/**",
    "iam/**",
    "**/migrations/**",
    "**/*lock*",
    "**/deploy*.sh",
    "**/deploy*.py",
]
MEDIUM_RISK_PATTERNS = [
    "**/pyproject.toml",
    "**/requirements*.txt",
    "**/package.json",
    "**/Cargo.toml",
    "**/go.mod",
    "**/go.sum",
    "**/composer.json",
]
EXCLUDE_FROM_RISK = ["docs/**", "README*", "*.md", "**/README*"]


def classify_risk_from_paths(
    touch_paths: list[str] | None,
) -> tuple[Literal["LOW", "MEDIUM", "HIGH"], list[str]]:
    """Classify risk from touch_paths. Empty → HIGH (unknown scope).

    Args:
        touch_paths: Paths touched by the plan (from read/edit/add steps)

    Returns:
        (risk_level, risk_drivers) — drivers are paths that matched high or medium
    """
    if not touch_paths:
        return ("HIGH", [])

    exclude_spec = PathSpec.from_lines("gitwildmatch", EXCLUDE_FROM_RISK)
    high_spec = PathSpec.from_lines("gitwildmatch", HIGH_RISK_PATTERNS)
    medium_spec = PathSpec.from_lines("gitwildmatch", MEDIUM_RISK_PATTERNS)

    paths_to_check: list[str] = []
    for p in touch_paths:
        path = p.lstrip("/") if p else ""
        if not path:
            continue
        if exclude_spec.match_file(path):
            continue
        paths_to_check.append(path)

    if not paths_to_check:
        return ("LOW", [])

    risk_drivers: list[str] = []
    high_matches: list[str] = []

    for path in paths_to_check:
        if high_spec.match_file(path):
            high_matches.append(path)
        elif medium_spec.match_file(path):
            risk_drivers.append(path)

    if high_matches:
        return ("HIGH", high_matches)
    if risk_drivers:
        return ("MEDIUM", risk_drivers)
    return ("LOW", [])
