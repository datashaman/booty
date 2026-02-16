"""Tests for memory lookup — query, path_match_score, fingerprint, retention, sort order."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from booty.memory.lookup import (
    derive_paths_hash,
    fingerprint_matches,
    normalize_path,
    path_match_score,
    query,
)
from booty.memory.store import append_record, read_records


# --- Path normalization and matching ---


def test_normalize_path_strips_and_removes_dot_slash():
    """normalize_path strips whitespace and removes ./ prefix."""
    assert normalize_path("  src/foo/bar  ") == "src/foo/bar"
    assert normalize_path("./a/b") == "a/b"


def test_path_match_score_exact_match():
    """Exact path match scores 2."""
    assert path_match_score(["src/foo"], ["src/foo"]) >= 2


def test_path_match_score_prefix_match():
    """Prefix/containment match scores 1."""
    assert path_match_score(["src/foo"], ["src/foo/new.py"]) >= 1


def test_fingerprint_matches():
    """fingerprint_matches compares non-empty strings."""
    assert fingerprint_matches("x", "x") is True
    assert fingerprint_matches("x", "y") is False
    assert fingerprint_matches("x", None) is False
    assert fingerprint_matches(None, "x") is False


def test_derive_paths_hash_length():
    """derive_paths_hash returns 16-char hex."""
    assert len(derive_paths_hash(["a.py", "b.py"])) == 16


# --- query() API ---


def test_query_empty_paths_and_fingerprint_returns_empty(monkeypatch, tmp_path):
    """query with no paths and no fingerprint returns []."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    result = query([], "owner/repo")
    assert result == []


def test_query_with_paths_no_records_returns_empty(monkeypatch, tmp_path):
    """query with paths but no records returns []."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    result = query(["src/foo.py"], "owner/repo")
    assert result == []


def test_query_with_paths_matching_record_returns_subset(monkeypatch, tmp_path):
    """query with paths matching record returns result subset."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    path = tmp_path / "memory.jsonl"
    now = datetime.now(timezone.utc)
    rec = {
        "type": "incident",
        "timestamp": now.isoformat(),
        "summary": "Sentry #1",
        "links": [{"url": "https://x", "type": "github_issue"}],
        "id": "r1",
        "repo": "owner/repo",
        "paths": ["src/foo.py"],
    }
    append_record(path, rec)

    result = query(["src/foo.py"], "owner/repo", state_dir=tmp_path)
    assert len(result) == 1
    r = result[0]
    assert set(r.keys()) == {"type", "timestamp", "summary", "links", "id"}
    assert r["type"] == "incident"
    assert r["summary"] == "Sentry #1"
    assert r["id"] == "r1"


def test_query_with_fingerprint_match(monkeypatch, tmp_path):
    """query with fingerprint finds matching record."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    path = tmp_path / "memory.jsonl"
    now = datetime.now(timezone.utc)
    rec = {
        "type": "governor_hold",
        "timestamp": now.isoformat(),
        "summary": "Held deploy",
        "links": [],
        "id": "r2",
        "repo": "owner/repo",
        "fingerprint": "reason:x",
    }
    append_record(path, rec)

    result = query([], "owner/repo", fingerprint="reason:x", state_dir=tmp_path)
    assert len(result) == 1
    assert result[0]["id"] == "r2"


def test_query_sort_order_severity_recency_path_overlap(monkeypatch, tmp_path):
    """Results sorted by severity desc, recency desc, path_overlap desc."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    path = tmp_path / "memory.jsonl"
    now = datetime.now(timezone.utc)
    base = {"repo": "owner/repo", "summary": "x", "links": [], "paths": ["src/foo"]}

    # critical (newer), high (older), low (newer, less path overlap)
    append_record(
        path,
        {
            **base,
            "type": "a",
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "severity": "critical",
            "id": "c1",
        },
    )
    append_record(
        path,
        {
            **base,
            "type": "b",
            "timestamp": (now - timedelta(days=2)).isoformat(),
            "severity": "high",
            "id": "h1",
        },
    )
    append_record(
        path,
        {
            **base,
            "type": "c",
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "severity": "low",
            "id": "l1",
        },
    )

    result = query(["src/foo"], "owner/repo", state_dir=tmp_path, max_matches=5)
    # critical first, then high, then low (result subset has type, timestamp, summary, links, id)
    assert result[0]["id"] == "c1"
    assert result[1]["id"] == "h1"
    assert result[2]["id"] == "l1"


def test_query_retention_filter_excludes_old_records(monkeypatch, tmp_path):
    """Records older than 90 days are excluded."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    path = tmp_path / "memory.jsonl"
    old = datetime.now(timezone.utc) - timedelta(days=100)
    rec = {
        "type": "incident",
        "timestamp": old.isoformat(),
        "summary": "old",
        "links": [],
        "id": "old1",
        "repo": "owner/repo",
        "paths": ["src/foo.py"],
    }
    append_record(path, rec)

    result = query(["src/foo.py"], "owner/repo", state_dir=tmp_path)
    assert result == []


def test_query_repo_filter(monkeypatch, tmp_path):
    """Only records matching repo are returned."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    path = tmp_path / "memory.jsonl"
    now = datetime.now(timezone.utc)
    rec = {
        "type": "incident",
        "timestamp": now.isoformat(),
        "summary": "x",
        "links": [],
        "id": "r1",
        "repo": "other/repo",
        "paths": ["src/foo.py"],
    }
    append_record(path, rec)

    result = query(["src/foo.py"], "owner/repo", state_dir=tmp_path)
    assert result == []

    result = query(["src/foo.py"], "other/repo", state_dir=tmp_path)
    assert len(result) == 1
    assert result[0]["id"] == "r1"


def test_query_max_matches_limit(monkeypatch, tmp_path):
    """query respects max_matches."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    path = tmp_path / "memory.jsonl"
    now = datetime.now(timezone.utc)
    for i in range(5):
        append_record(
            path,
            {
                "type": "incident",
                "timestamp": (now - timedelta(days=i)).isoformat(),
                "summary": f"x{i}",
                "links": [],
                "id": f"r{i}",
                "repo": "owner/repo",
                "paths": ["src/foo.py"],
            },
        )

    result = query(
        ["src/foo.py"], "owner/repo", state_dir=tmp_path, max_matches=2
    )
    assert len(result) == 2
