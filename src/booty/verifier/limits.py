"""Diff limit enforcement for Verifier — max_files_changed, max_diff_loc, max_loc_per_file."""

from dataclasses import dataclass

from pathspec import PathSpec

from booty.test_runner.config import BootyConfig, BootyConfigV1

DEFAULT_MAX_FILES_CHANGED = 12
DEFAULT_MAX_DIFF_LOC = 600
DEFAULT_MAX_LOC_PER_FILE = 250
DEFAULT_MAX_LOC_PER_FILE_EXCLUDE = ["tests/**"]


@dataclass
class FileDiff:
    """Per-file diff stats."""

    filename: str
    additions: int
    deletions: int


@dataclass
class DiffStats:
    """Aggregate diff stats for a PR."""

    files_changed: int
    additions: int
    deletions: int
    files: list[FileDiff]


@dataclass
class LimitFailure:
    """Single limit violation with fix hint."""

    rule: str
    observed: int
    limit: int
    fix_hint: str


@dataclass
class LimitsConfig:
    """Limit configuration with defaults."""

    max_files_changed: int = DEFAULT_MAX_FILES_CHANGED
    max_diff_loc: int = DEFAULT_MAX_DIFF_LOC
    max_loc_per_file: int | None = DEFAULT_MAX_LOC_PER_FILE
    max_loc_per_file_pathspec: list[str] | None = None


def get_pr_diff_stats(repo, pr_number: int) -> DiffStats:
    """Fetch diff stats from a PyGithub PR.

    Args:
        repo: github.Repository.Repository instance
        pr_number: Pull request number

    Returns:
        DiffStats with files_changed, additions, deletions, per-file stats
    """
    pr = repo.get_pull(pr_number)
    files = [
        FileDiff(f.filename, f.additions, f.deletions)
        for f in pr.get_files()
    ]
    return DiffStats(
        files_changed=pr.changed_files,
        additions=pr.additions,
        deletions=pr.deletions,
        files=files,
    )


def check_diff_limits(stats: DiffStats, limits: LimitsConfig) -> list[LimitFailure]:
    """Check diff stats against limits; return list of violations."""
    failures: list[LimitFailure] = []

    if stats.files_changed > limits.max_files_changed:
        failures.append(
            LimitFailure(
                rule="max_files_changed",
                observed=stats.files_changed,
                limit=limits.max_files_changed,
                fix_hint="split PR or raise limit in .booty.yml",
            )
        )

    diff_loc = stats.additions + stats.deletions
    if diff_loc > limits.max_diff_loc:
        failures.append(
            LimitFailure(
                rule="max_diff_loc",
                observed=diff_loc,
                limit=limits.max_diff_loc,
                fix_hint="reduce diff or raise limit in .booty.yml",
            )
        )

    if limits.max_loc_per_file is not None:
        exclude_patterns = limits.max_loc_per_file_pathspec or DEFAULT_MAX_LOC_PER_FILE_EXCLUDE
        spec = PathSpec.from_lines("gitwildmatch", exclude_patterns)
        for f in stats.files:
            if spec.match_file(f.filename):
                continue
            total = f.additions + f.deletions
            if total > limits.max_loc_per_file:
                failures.append(
                    LimitFailure(
                        rule="max_loc_per_file",
                        observed=total,
                        limit=limits.max_loc_per_file,
                        fix_hint=f"{f.filename}: split or raise limit",
                    )
                )

    return failures


def format_limit_failures(failures: list[LimitFailure]) -> str:
    """Format limit failures for check output.

    Format per CONTEXT:
      FAILED: {rule}
      Observed: {observed}
      Limit: {limit}
      Fix: {fix_hint}
    """
    blocks = []
    for f in failures:
        blocks.append(
            f"FAILED: {f.rule}\n"
            f"Observed: {f.observed}\n"
            f"Limit: {f.limit}\n"
            f"Fix: {f.fix_hint}"
        )
    return "\n\n".join(blocks)


def limits_config_from_booty_config(
    config: BootyConfig | BootyConfigV1,
) -> LimitsConfig:
    """Extract LimitsConfig from BootyConfig/BootyConfigV1; use defaults when None."""
    max_files = getattr(config, "max_files_changed", None)
    max_diff = getattr(config, "max_diff_loc", None)
    max_loc = getattr(config, "max_loc_per_file", None)
    pathspec = getattr(config, "max_loc_per_file_pathspec", None)

    return LimitsConfig(
        max_files_changed=max_files if max_files is not None else DEFAULT_MAX_FILES_CHANGED,
        max_diff_loc=max_diff if max_diff is not None else DEFAULT_MAX_DIFF_LOC,
        max_loc_per_file=max_loc if max_loc is not None else DEFAULT_MAX_LOC_PER_FILE,
        max_loc_per_file_pathspec=pathspec,
    )
