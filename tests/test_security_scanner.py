"""Tests for security scanner module."""

import subprocess
from unittest.mock import patch

import pytest

from booty.security.scanner import build_annotations, run_secret_scan, ScanResult


class TestBuildAnnotations:
    """build_annotations tests."""

    def test_empty_findings(self) -> None:
        """build_annotations with 0 findings returns empty list and no suffix."""
        a, s = build_annotations([], 50)
        assert a == []
        assert s == ""

    def test_one_finding(self) -> None:
        """build_annotations with 1 finding returns one annotation."""
        finding = {"path": "x", "start_line": 1, "end_line": 1, "rule_id": "r"}
        a, s = build_annotations([finding], 50)
        assert len(a) == 1
        assert a[0]["path"] == "x"
        assert a[0]["start_line"] == 1
        assert a[0]["annotation_level"] == "failure"
        assert s == ""

    def test_cap_50_and_more_suffix(self) -> None:
        """build_annotations with 51 findings caps at 50, suffix 'and N more'."""
        findings = [
            {"path": f"f{i}.py", "start_line": i, "end_line": i, "rule_id": "r"}
            for i in range(51)
        ]
        a, s = build_annotations(findings, 50)
        assert len(a) == 50
        assert s == " and 1 more"


class TestRunSecretScan:
    """run_secret_scan tests."""

    def test_missing_binary_returns_scan_ok_false(self) -> None:
        """When both gitleaks and trufflehog missing, ScanResult.scan_ok=False."""
        with patch("booty.security.scanner.shutil.which", return_value=None):
            r = run_secret_scan(".", "HEAD^", "HEAD", None)
        assert r.scan_ok is False
        assert r.error_message is not None
        assert "not found" in r.error_message.lower()

    def test_nonexistent_workspace(self) -> None:
        """Non-existent workspace returns scan_ok=False."""
        r = run_secret_scan("/nonexistent/path/xyz", "HEAD^", "HEAD", None)
        assert r.scan_ok is False
        assert "not found" in (r.error_message or "").lower()

    def test_clean_dir_or_empty_diff(self) -> None:
        """In real repo with clean diff, scan completes (scan_ok True or binary missing)."""
        r = run_secret_scan(".", "HEAD", "HEAD", None)
        # Empty diff (base==head) → no diff content → ScanResult(ok=True, findings=[])
        assert hasattr(r, "findings")
        assert hasattr(r, "scan_ok")
        if r.scan_ok:
            assert r.findings == []
