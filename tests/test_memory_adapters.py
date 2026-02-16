"""Tests for memory adapters (build_*_record)."""

from types import SimpleNamespace

import pytest

from booty.memory.adapters import (
    build_deploy_failure_record,
    build_governor_hold_record,
    build_incident_record,
    build_revert_record,
    build_security_block_record,
    build_verifier_cluster_record,
)


def test_build_incident_record_basic():
    """build_incident_record returns type, repo, source, fingerprint."""
    r = build_incident_record({"level": "error", "issue_id": "x"}, 42, "owner/repo")
    assert r["type"] == "incident"
    assert r["repo"] == "owner/repo"
    assert r["source"] == "observability"
    assert "fingerprint" in r
    assert r["links"] == [{"url": "https://github.com/owner/repo/issues/42", "type": "github_issue"}]


def test_build_incident_record_handles_missing_fields():
    """build_incident_record handles missing fields."""
    r = build_incident_record({}, 1, "a/b")
    assert r["type"] == "incident"
    assert r["severity"] == "error"
    assert r["fingerprint"] == ""
    assert r["sha"] == ""
    assert r["pr_number"] is None


def test_build_governor_hold_record():
    """build_governor_hold_record asserts sha, reason in title."""
    d = SimpleNamespace(outcome="HOLD", reason="high_risk", risk_class="HIGH", sha="abc1234")
    r = build_governor_hold_record(d, "owner/repo")
    assert r["type"] == "governor_hold"
    assert r["sha"] == "abc1234"
    assert "high_risk" in r["title"]
    assert r["metadata"]["reason"] == "high_risk"
    assert r["metadata"]["risk_class"] == "HIGH"


def test_build_deploy_failure_record():
    """build_deploy_failure_record asserts metadata.conclusion, failure_type."""
    r = build_deploy_failure_record(
        "abc123", "https://example.com/run", "failure", "deploy:health-check-failed", "o/r"
    )
    assert r["type"] == "deploy_failure"
    assert r["metadata"]["conclusion"] == "failure"
    assert r["metadata"]["failure_type"] == "deploy:health-check-failed"


def test_build_security_block_record():
    """build_security_block_record assert trigger in metadata, paths."""
    j = SimpleNamespace(owner="o", repo_name="r", head_sha="abc123", pr_number=1)
    r = build_security_block_record(j, "secret", "Secret detected", "summary", ["a.py", "b.py"])
    assert r["type"] == "security_block"
    assert r["metadata"]["trigger"] == "secret"
    assert r["paths"] == ["a.py", "b.py"]


def test_build_verifier_cluster_record():
    """build_verifier_cluster_record assert fingerprint contains failure_type."""
    j = SimpleNamespace(owner="o", repo_name="r", head_sha="abc123", pr_number=1)
    r = build_verifier_cluster_record(j, "compile", ["x.py"], "compile failed")
    assert r["type"] == "verifier_cluster"
    assert "compile" in r["fingerprint"]


def test_build_revert_record():
    """build_revert_record assert reverted_sha in metadata."""
    r = build_revert_record("o/r", "abc123", "def456", "push")
    assert r["type"] == "revert"
    assert r["metadata"]["reverted_sha"] == "def456"
    assert r["source"] == "push"
