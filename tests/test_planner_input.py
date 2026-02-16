"""Tests for planner input normalization."""

import pytest

from booty.planner.input import (
    PlannerInput,
    _extract_incident_fields,
    _looks_like_sentry_body,
    _looks_like_sentry_title,
    derive_source_type,
    get_repo_context,
    normalize_cli_text,
    normalize_from_job,
    normalize_github_issue,
)
from booty.planner.jobs import PlannerJob


def test_planner_input_validation() -> None:
    """PlannerInput accepts valid fields."""
    inp = PlannerInput(
        goal="Fix bug",
        body="Description",
        labels=["bug"],
        source_type="bug",
        metadata={"owner": "o", "repo": "r"},
    )
    assert inp.goal == "Fix bug"
    assert inp.source_type == "bug"


def test_derive_source_type_label_incident() -> None:
    """agent:incident label -> incident."""
    assert derive_source_type(["agent:incident"], "", "") == "incident"


def test_derive_source_type_label_bug() -> None:
    """bug label -> bug."""
    assert derive_source_type(["bug"], "", "") == "bug"


def test_derive_source_type_label_enhancement() -> None:
    """enhancement label -> feature_request."""
    assert derive_source_type(["enhancement"], "", "") == "feature_request"


def test_derive_source_type_heuristics_sentry_body() -> None:
    """Body with Severity + Sentry markers -> incident."""
    body = "**Severity:** x\n**Sentry:** https://a.b"
    assert derive_source_type([], body, "") == "incident"


def test_derive_source_type_heuristics_single_marker_not_enough() -> None:
    """Single marker (Severity only) -> unknown (pitfall: need 2+ markers)."""
    body = "**Severity:** x"
    assert derive_source_type([], body, "") == "unknown"


def test_derive_source_type_sentry_title() -> None:
    """Title [error] bracket pattern -> incident."""
    assert derive_source_type([], "", "[error] Exception — foo.py") == "incident"


def test_derive_source_type_unknown() -> None:
    """No label match, no heuristics -> unknown."""
    assert derive_source_type([], "plain text", "Plain title") == "unknown"


def test_extract_incident_fields() -> None:
    """Extract location and sentry_url from body."""
    body = "**Location:** foo.py\n**Sentry:** https://sentry.io/x"
    fields = _extract_incident_fields(body)
    assert fields.get("location") == "foo.py"
    assert "sentry" in (fields.get("sentry_url") or "")


def test_extract_incident_fields_missing_gracefully() -> None:
    """Handle missing markers gracefully."""
    fields = _extract_incident_fields("plain body")
    assert fields == {}


def test_normalize_github_issue_full() -> None:
    """normalize_github_issue with full issue dict."""
    issue = {
        "title": "Fix bug",
        "body": "Description here",
        "labels": [{"name": "bug"}, {"name": "urgent"}],
        "html_url": "https://github.com/o/r/issues/1",
        "number": 1,
    }
    inp = normalize_github_issue(issue)
    assert inp.goal == "Fix bug"
    assert inp.body == "Description here"
    assert inp.labels == ["bug", "urgent"]
    assert inp.source_type == "bug"
    assert inp.metadata.get("issue_url")
    assert inp.metadata.get("issue_number") == 1


def test_normalize_cli_text_multiline() -> None:
    """normalize_cli_text goal/body split (first line vs remainder)."""
    inp = normalize_cli_text("First line\nRest of text")
    assert inp.goal == "First line"
    assert "Rest" in inp.body


def test_normalize_cli_text_single_line() -> None:
    """Single line CLI text -> all goal, empty body."""
    inp = normalize_cli_text("Single")
    assert inp.goal == "Single"
    assert inp.body == ""


def test_normalize_cli_text_body_trim() -> None:
    """Body trim to 8000 chars."""
    long_body = "x" * 10000
    inp = normalize_cli_text(f"Goal\n{long_body}")
    assert len(inp.body) == 8000


def test_normalize_cli_text_goal_trim() -> None:
    """Goal trim to 200 chars."""
    long_goal = "a" * 250
    inp = normalize_cli_text(long_goal)
    assert len(inp.goal) == 200


def test_normalize_from_job() -> None:
    """normalize_from_job with PlannerJob payload."""
    job = PlannerJob(
        "j1", 1, "url", "repo_url", "owner", "repo",
        {"issue": {"title": "T", "body": "B", "labels": []}},
    )
    inp = normalize_from_job(job)
    assert inp.goal == "T"
    assert inp.body == "B"
    assert inp.metadata.get("owner") == "owner"
    assert inp.metadata.get("repo") == "repo"


def test_normalize_github_issue_repo_context_passthrough() -> None:
    """normalize_github_issue passes repo_context to PlannerInput."""
    inp = normalize_github_issue(
        {"title": "x", "body": "", "labels": []},
        repo_info={"owner": "o", "repo": "r"},
        repo_context={"default_branch": "main", "tree": []},
    )
    assert inp.repo_context == {"default_branch": "main", "tree": []}


def test_looks_like_sentry_body_both_markers() -> None:
    """_looks_like_sentry_body requires both markers."""
    assert _looks_like_sentry_body("**Severity:** x\n**Sentry:** y") is True
    assert _looks_like_sentry_body("**Severity:** x only") is False
    assert _looks_like_sentry_body("**Sentry:** y only") is False


def test_looks_like_sentry_title_pattern() -> None:
    """_looks_like_sentry_title matches bracket prefix."""
    assert _looks_like_sentry_title("[error] foo") is True
    assert _looks_like_sentry_title("[warning] bar") is True
    assert _looks_like_sentry_title("plain title") is False


def test_get_repo_context_returns_none_on_invalid_token() -> None:
    """get_repo_context returns None when token invalid or repo unreachable."""
    ctx = get_repo_context("nonexistent", "norepo", "invalid-token")
    assert ctx is None
