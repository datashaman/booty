"""Tests for permission drift detection."""

import git
import pytest

from booty.security.permission_drift import (
    _title_for_paths,
    get_changed_paths,
    sensitive_paths_touched,
)


class TestSensitivePathsTouched:
    """sensitive_paths_touched tests."""

    def test_empty_paths(self) -> None:
        """Empty paths returns empty list."""
        assert sensitive_paths_touched([], [".github/workflows/**"]) == []

    def test_empty_sensitive_paths(self) -> None:
        """Empty sensitive_paths returns empty list."""
        assert sensitive_paths_touched([("foo.py", None)], []) == []

    def test_match_added_file(self) -> None:
        """Added workflow file matches."""
        paths = [(".github/workflows/ci.yml", None)]
        spec = [".github/workflows/**"]
        assert sensitive_paths_touched(paths, spec) == [".github/workflows/ci.yml"]

    def test_no_match(self) -> None:
        """Non-matching path returns empty."""
        paths = [("src/foo.py", None)]
        spec = [".github/workflows/**"]
        assert sensitive_paths_touched(paths, spec) == []

    def test_rename_old_path_sensitive(self) -> None:
        """Rename from sensitive path matches old path."""
        paths = [("src/bar.py", ".github/workflows/old.yml")]
        spec = [".github/workflows/**"]
        assert sensitive_paths_touched(paths, spec) == [".github/workflows/old.yml"]

    def test_rename_new_path_sensitive(self) -> None:
        """Rename to sensitive path matches new path."""
        paths = [(".github/workflows/new.yml", "src/old.py")]
        spec = [".github/workflows/**"]
        assert sensitive_paths_touched(paths, spec) == [".github/workflows/new.yml"]

    def test_deduplicated(self) -> None:
        """Duplicate matches are deduplicated."""
        paths = [
            (".github/workflows/a.yml", None),
            (".github/workflows/b.yml", None),
        ]
        spec = [".github/workflows/**"]
        assert sensitive_paths_touched(paths, spec) == [
            ".github/workflows/a.yml",
            ".github/workflows/b.yml",
        ]


class TestTitleForPaths:
    """_title_for_paths tests."""

    def test_workflow(self) -> None:
        """Workflow path gets workflow modified title."""
        assert "workflow modified" in _title_for_paths([".github/workflows/ci.yml"])

    def test_infra(self) -> None:
        """Infra path gets infra modified title."""
        assert "infra modified" in _title_for_paths(["infra/foo.tf"])

    def test_terraform(self) -> None:
        """Terraform path gets terraform modified title."""
        assert "terraform modified" in _title_for_paths(["terraform/main.tf"])

    def test_default(self) -> None:
        """Unknown prefix gets default title."""
        t = _title_for_paths(["other/path.py"])
        assert "Security escalated" in t
        assert "permission surface changed" in t

    def test_empty_paths(self) -> None:
        """Empty paths returns default."""
        t = _title_for_paths([])
        assert "Security escalated" in t


class TestGetChangedPaths:
    """get_changed_paths tests — uses real git repo."""

    def test_empty_diff(self) -> None:
        """Same base and head returns empty."""
        repo = git.Repo(".")
        try:
            head = repo.head.commit.hexsha
            out = get_changed_paths(repo, head, head)
            assert out == []
        finally:
            repo.close()

    def test_diff_has_paths(self) -> None:
        """Diff between commits returns path tuples."""
        repo = git.Repo(".")
        try:
            commits = list(repo.iter_commits(max_count=2))
            if len(commits) < 2:
                pytest.skip("Repo has fewer than 2 commits")
            base, head = commits[1].hexsha, commits[0].hexsha
            out = get_changed_paths(repo, base, head)
            assert isinstance(out, list)
            for item in out:
                assert isinstance(item, tuple)
                assert len(item) == 2
                assert isinstance(item[0], str)
                assert item[1] is None or isinstance(item[1], str)
        finally:
            repo.close()
