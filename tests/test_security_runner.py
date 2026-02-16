"""Tests for Security runner."""

import pytest

from booty.security.audit import AuditResult
from booty.security.runner import build_audit_summary, process_security_job


def test_process_security_job_callable() -> None:
    """process_security_job is callable."""
    assert callable(process_security_job)


def test_build_audit_summary_with_failures() -> None:
    """build_audit_summary produces CONTEXT-compliant summary for failures."""
    r = AuditResult(
        ok=False,
        findings=[
            {"ecosystem": "python", "path": "pkg/requirements.txt", "severity": "high"},
            {"ecosystem": "python", "path": "pkg/requirements.txt", "severity": "critical"},
        ],
        errors=["pip-audit not found — install to enable Python dependency audit"],
        summary_by_ecosystem={},
        worst_severity="critical",
    )
    summary = build_audit_summary(r)
    assert "python" in summary
    assert "critical" in summary or "high" in summary
    assert "Affected" in summary or "pkg" in summary
    assert "pip-audit" in summary or "Errors" in summary


def test_build_audit_summary_tool_missing_only() -> None:
    """build_audit_summary shows errors when tool missing, no findings."""
    r = AuditResult(
        ok=False,
        findings=[],
        errors=["pip-audit not found — install to enable Python dependency audit"],
        summary_by_ecosystem={},
        worst_severity=None,
    )
    summary = build_audit_summary(r)
    assert "pip-audit" in summary or "Errors" in summary
