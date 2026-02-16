"""Tests for security audit module."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from booty.security.audit import (
    AuditResult,
    discover_lockfiles,
    run_dependency_audit,
)


class TestDiscoverLockfiles:
    """discover_lockfiles tests."""

    def test_in_booty_repo_finds_lockfiles(self) -> None:
        """discover_lockfiles in booty repo finds pyproject/uv.lock or package-lock."""
        found = discover_lockfiles(Path("."))
        assert isinstance(found, list)
        for eco, p in found:
            assert eco in ("python", "node", "php", "rust")
            assert p.exists()

    def test_deduplication_by_hash(self) -> None:
        """Identical lockfiles (same content) are deduplicated."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            content = b"deps"
            (td / "requirements.txt").write_bytes(content)
            sub = td / "sub"
            sub.mkdir()
            (sub / "requirements.txt").write_bytes(content)  # same content
            found = discover_lockfiles(td)
            reqs = [(e, p) for e, p in found if p.name == "requirements.txt"]
            # Hash dedup: same content -> one result
            assert len(reqs) == 1

    def test_empty_or_missing_dir(self) -> None:
        """Non-existent or empty dir returns empty list."""
        assert discover_lockfiles(Path("/nonexistent")) == []
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            found = discover_lockfiles(Path(tmp))
            assert found == []


class TestAuditResult:
    """AuditResult dataclass tests."""

    def test_ok_true(self) -> None:
        """AuditResult with ok=True."""
        r = AuditResult(
            ok=True,
            findings=[],
            errors=[],
            summary_by_ecosystem={},
            worst_severity=None,
        )
        assert r.ok

    def test_required_fields(self) -> None:
        """AuditResult has findings, errors, worst_severity."""
        r = AuditResult(
            ok=False,
            findings=[{"ecosystem": "python", "severity": "high"}],
            errors=["pip-audit not found"],
            summary_by_ecosystem={"python:x": "error"},
            worst_severity="high",
        )
        assert r.findings
        assert r.errors
        assert r.worst_severity == "high"


class TestRunDependencyAudit:
    """run_dependency_audit tests."""

    def test_missing_tool_errors(self) -> None:
        """When pip-audit missing, errors list includes clear message."""
        with patch("booty.security.audit.shutil.which", return_value=None):
            r = run_dependency_audit(".", None)
        assert not r.ok or "not found" in str(r.errors) or "not installed" in str(r.errors)
        assert any(
            "pip-audit" in e or "not found" in e or "not installed" in e
            for e in r.errors
        )

    def test_returns_audit_result_struct(self) -> None:
        """run_dependency_audit returns AuditResult with expected fields."""
        r = run_dependency_audit(".", None)
        assert hasattr(r, "ok")
        assert hasattr(r, "findings")
        assert hasattr(r, "errors")
        assert hasattr(r, "worst_severity")
        assert hasattr(r, "summary_by_ecosystem")

    def test_mock_pip_audit_json_parsing(self) -> None:
        """Mock pip-audit JSON output; assert severity filter."""
        with (
            patch("booty.security.audit.shutil.which", return_value="/usr/bin/pip-audit"),
            patch(
                "booty.security.audit.subprocess.run",
                return_value=type("R", (), {"returncode": 1, "stdout": json.dumps([
                    {"name": "pkg1", "version": "1.0", "vulns": [{"id": "PYSEC-1"}]},
                ]), "stderr": ""})(),
            ),
        ):
            from booty.security.audit import _run_python_audit
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".lock", delete=False) as f:
                f.write(b" ")
                path = Path(f.name)
            try:
                findings, errors, summary = _run_python_audit(path, "high")
                assert len(findings) >= 1
                assert findings[0].get("severity") == "high"
            finally:
                path.unlink(missing_ok=True)
