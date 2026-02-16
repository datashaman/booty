"""Tests for memory surfacing — PR comment, Governor, Observability."""

import pytest
from unittest.mock import patch, MagicMock

from booty.memory.surfacing import (
    format_matches_for_pr,
    surface_pr_comment,
)


class TestFormatMatchesForPr:
    def test_empty_list_returns_empty_string(self):
        assert format_matches_for_pr([]) == ""

    def test_single_match_formats_correctly(self):
        matches = [
            {
                "type": "incident",
                "timestamp": "2024-01-15T10:00:00Z",
                "summary": "Database timeout",
                "links": ["https://github.com/o/r/issues/42"],
                "id": "mem-1",
            },
        ]
        result = format_matches_for_pr(matches)
        assert "incident" in result
        assert "Database timeout" in result
        assert "2024-01-15" in result
        assert "https://github.com/o/r/issues/42" in result

    def test_multiple_matches_formats_all(self):
        matches = [
            {"type": "incident", "timestamp": "2024-01-15T10:00:00Z", "summary": "A", "links": [], "id": "1"},
            {"type": "governor_hold", "timestamp": "2024-01-14T09:00:00Z", "summary": "B", "links": ["https://x"], "id": "2"},
        ]
        result = format_matches_for_pr(matches)
        assert "incident" in result and "A" in result
        assert "governor_hold" in result and "B" in result
        assert result.count("- **") == 2


class TestSurfacePrComment:
    @patch("booty.memory.surfacing.lookup")
    def test_comment_on_pr_false_does_nothing(self, mock_lookup):
        config = MagicMock()
        config.comment_on_pr = False
        surface_pr_comment("token", "https://github.com/o/r", 1, ["a.py"], "o/r", config)
        mock_lookup.query.assert_not_called()

    @patch("booty.memory.surfacing.post_memory_comment")
    @patch("booty.memory.surfacing.lookup")
    def test_zero_matches_does_not_call_post(self, mock_lookup, mock_post):
        mock_lookup.query.return_value = []
        config = MagicMock()
        config.comment_on_pr = True
        surface_pr_comment("token", "https://github.com/o/r", 1, ["a.py"], "o/r", config)
        mock_post.assert_not_called()

    @patch("booty.memory.surfacing.post_memory_comment")
    @patch("booty.memory.surfacing.lookup")
    def test_with_matches_calls_post_with_formatted_body(self, mock_lookup, mock_post):
        matches = [
            {"type": "incident", "timestamp": "2024-01-15T10:00:00Z", "summary": "x", "links": ["https://a"], "id": "1"},
        ]
        mock_lookup.query.return_value = matches
        config = MagicMock()
        config.comment_on_pr = True
        surface_pr_comment("token", "https://github.com/o/r", 1, ["a.py"], "o/r", config)
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "token"
        assert call_args[0][1] == "https://github.com/o/r"
        assert call_args[0][2] == 1
        body = call_args[0][3]
        assert "incident" in body
        assert "x" in body
