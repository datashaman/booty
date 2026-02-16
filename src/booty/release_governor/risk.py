"""Risk scoring from paths touched vs production_sha (GOV-05, GOV-06, GOV-07)."""

from typing import Literal

from pathspec import PathSpec

from booty.test_runner.config import ReleaseGovernorConfig


def compute_risk_class(
    comparison, config: ReleaseGovernorConfig
) -> Literal["LOW", "MEDIUM", "HIGH"]:
    """Compute risk class from diff (comparison) vs config pathspecs.

    Args:
        comparison: PyGithub Compare object (repo.compare(base, head));
            has .files with .filename per file.
        config: ReleaseGovernorConfig with high_risk_paths and medium_risk_paths.

    Returns:
        "LOW", "MEDIUM", or "HIGH". Empty diff -> LOW.
        Multi-category match takes highest risk.
    """
    files = getattr(comparison, "files", None)
    if not files or len(files) == 0:
        return "LOW"

    high_spec = PathSpec.from_lines("gitwildmatch", config.high_risk_paths)
    medium_spec = PathSpec.from_lines("gitwildmatch", config.medium_risk_paths)

    max_risk: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    for f in files:
        path = getattr(f, "filename", None) or (f if isinstance(f, str) else "")
        if not path:
            continue
        if high_spec.match_file(path):
            return "HIGH"
        if medium_spec.match_file(path):
            max_risk = "MEDIUM"

    return max_risk


def get_risk_paths(comparison, config: ReleaseGovernorConfig) -> list[str]:
    """Return filenames matching high or medium risk pathspecs (for --show-paths).

    Args:
        comparison: PyGithub Compare object
        config: ReleaseGovernorConfig

    Returns:
        Sorted list of paths that drove risk classification
    """
    files = getattr(comparison, "files", None)
    if not files:
        return []
    high_spec = PathSpec.from_lines("gitwildmatch", config.high_risk_paths)
    medium_spec = PathSpec.from_lines("gitwildmatch", config.medium_risk_paths)
    paths: list[str] = []
    for f in files:
        path = getattr(f, "filename", None) or (f if isinstance(f, str) else "")
        if not path:
            continue
        if high_spec.match_file(path) or medium_spec.match_file(path):
            paths.append(path)
    return sorted(paths)
