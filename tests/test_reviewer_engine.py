"""Tests for Reviewer engine — decision logic and block_on mapping."""

from unittest.mock import MagicMock, patch

from booty.reviewer.engine import BLOCK_ON_TO_CATEGORY, run_review
from booty.reviewer.schema import CategoryResult, Finding, ReviewResult


def _make_categories(
    overengineering: str = "PASS",
    architectural_drift: str = "PASS",
    tests: str = "PASS",
    duplication: str = "PASS",
    maintainability: str = "PASS",
    naming_api: str = "PASS",
) -> list[CategoryResult]:
    """Build 6 CategoryResult with specified grades."""
    names = [
        "Overengineering",
        "Architectural drift",
        "Tests",
        "Duplication",
        "Maintainability",
        "Naming/API",
    ]
    grades = [
        overengineering,
        architectural_drift,
        tests,
        duplication,
        maintainability,
        naming_api,
    ]
    return [
        CategoryResult(category=n, grade=g, findings=[])
        for n, g in zip(names, grades)
    ]


@patch("booty.reviewer.engine._review_diff_impl")
def test_block_on_mapping(mock_impl: MagicMock) -> None:
    """block_on ['overengineering'] + Overengineering FAIL → BLOCKED."""
    mock_impl.return_value = type("_", (), {"categories": _make_categories(overengineering="FAIL")})()
    result = run_review("diff", {"title": "", "body": "", "base_sha": "a", "head_sha": "b", "file_list": ""}, ["overengineering"])
    assert result.decision == "BLOCKED"
    assert "Overengineering" in result.blocking_categories


@patch("booty.reviewer.engine._review_diff_impl")
def test_block_on_empty_never_blocks(mock_impl: MagicMock) -> None:
    """block_on [] + any FAIL → APPROVED_WITH_SUGGESTIONS max."""
    mock_impl.return_value = type("_", (), {"categories": _make_categories(overengineering="FAIL")})()
    result = run_review("diff", {"title": "", "body": "", "base_sha": "a", "head_sha": "b", "file_list": ""}, [])
    assert result.decision == "APPROVED_WITH_SUGGESTIONS"
    assert result.blocking_categories == []


@patch("booty.reviewer.engine._review_diff_impl")
def test_maintainability_never_blocks(mock_impl: MagicMock) -> None:
    """Maintainability FAIL, block_on empty → APPROVED_WITH_SUGGESTIONS."""
    mock_impl.return_value = type("_", (), {"categories": _make_categories(maintainability="FAIL")})()
    result = run_review("diff", {"title": "", "body": "", "base_sha": "a", "head_sha": "b", "file_list": ""}, [])
    assert result.decision == "APPROVED_WITH_SUGGESTIONS"
    assert result.blocking_categories == []


@patch("booty.reviewer.engine._review_diff_impl")
def test_all_pass_approved(mock_impl: MagicMock) -> None:
    """All PASS → APPROVED."""
    mock_impl.return_value = type("_", (), {"categories": _make_categories()})()
    result = run_review("diff", {"title": "", "body": "", "base_sha": "a", "head_sha": "b", "file_list": ""}, ["overengineering"])
    assert result.decision == "APPROVED"


@patch("booty.reviewer.engine._review_diff_impl")
def test_warn_approval_with_suggestions(mock_impl: MagicMock) -> None:
    """Any WARN, block_on has that category but grade WARN → APPROVED_WITH_SUGGESTIONS."""
    mock_impl.return_value = type("_", (), {"categories": _make_categories(overengineering="WARN")})()
    result = run_review("diff", {"title": "", "body": "", "base_sha": "a", "head_sha": "b", "file_list": ""}, ["overengineering"])
    assert result.decision == "APPROVED_WITH_SUGGESTIONS"
