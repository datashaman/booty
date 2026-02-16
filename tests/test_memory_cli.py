"""Tests for memory CLI — booty memory status, booty memory query."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from booty.cli import cli
from booty.memory.store import append_record, read_records


def test_memory_status_disabled_when_no_config(tmp_path):
    """With no .booty.yml, status prints 'Memory disabled' and exits 0."""
    runner = CliRunner()
    with runner.isolated_filesystem(tmp_path):
        result = runner.invoke(cli, ["memory", "status"], obj={})
        assert result.exit_code == 0
        assert "Memory disabled" in result.output


def test_memory_status_disabled_when_memory_block_missing(tmp_path):
    """With .booty.yml without memory block, status prints 'Memory disabled'."""
    runner = CliRunner()
    with runner.isolated_filesystem(tmp_path):
        (Path(tmp_path) / ".booty.yml").write_text("schema_version: 1\ntest_command: pytest\n")
        result = runner.invoke(cli, ["memory", "status", "--workspace", str(tmp_path)], obj={})
        assert result.exit_code == 0
        assert "Memory disabled" in result.output


def test_memory_status_enabled_shows_records_retention(monkeypatch, tmp_path):
    """With memory enabled and records, status prints enabled, records, retention_days."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    config_dir = tmp_path / "ws"
    config_dir.mkdir()
    (config_dir / ".booty.yml").write_text(
        "schema_version: 1\ntest_command: pytest\nmemory:\n  enabled: true\n  retention_days: 90\n"
    )
    path = tmp_path / "memory.jsonl"
    now = datetime.now(timezone.utc)
    append_record(path, {"type": "incident", "timestamp": now.isoformat(), "summary": "x", "repo": "o/r", "paths": []})

    runner = CliRunner()
    result = runner.invoke(cli, ["memory", "status", "--workspace", str(config_dir)], obj={})
    assert result.exit_code == 0
    assert "enabled: true" in result.output
    assert "records: 1" in result.output
    assert "retention_days: 90" in result.output


def test_memory_status_json_output(monkeypatch, tmp_path):
    """status --json outputs valid JSON with enabled, records, retention_days."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    config_dir = tmp_path / "ws"
    config_dir.mkdir()
    (config_dir / ".booty.yml").write_text(
        "schema_version: 1\ntest_command: pytest\nmemory:\n  enabled: true\n  retention_days: 60\n"
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["memory", "status", "--workspace", str(config_dir), "--json"], obj={})
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["enabled"] is True
    assert "records" in data
    assert data["retention_days"] == 60


def test_memory_query_both_pr_and_sha_raises():
    """Invoking query with both --pr and --sha raises UsageError."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["memory", "query", "--pr", "1", "--sha", "abc123", "--repo", "o/r"], obj={}
    )
    assert result.exit_code != 0
    assert "exactly one" in result.output.lower() or "UsageError" in str(type(result.exc_info))


def test_memory_query_neither_pr_nor_sha_raises():
    """Invoking query with neither --pr nor --sha raises UsageError."""
    runner = CliRunner()
    result = runner.invoke(cli, ["memory", "query", "--repo", "o/r"], obj={})
    assert result.exit_code != 0


def test_memory_query_missing_repo_when_not_in_git(tmp_path):
    """Without --repo and not in git repo, query prints 'Use --repo owner/repo'."""
    runner = CliRunner()
    with runner.isolated_filesystem(tmp_path):
        with patch("booty.cli._infer_repo_from_git", return_value=None):
            result = runner.invoke(cli, ["memory", "query", "--pr", "1", "--workspace", str(tmp_path)], obj={})
        assert result.exit_code == 1
        assert "repo" in result.output.lower()


def test_memory_query_github_token_required():
    """Without GITHUB_TOKEN, query prints 'GITHUB_TOKEN required' and exits 1."""
    runner = CliRunner()
    with patch("booty.cli.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(GITHUB_TOKEN="")
        result = runner.invoke(cli, ["memory", "query", "--pr", "1", "--repo", "o/r"], obj={})
    assert result.exit_code == 1
    assert "GITHUB_TOKEN" in result.output


def test_memory_query_memory_disabled_exits_cleanly(tmp_path):
    """When memory disabled, query prints 'Memory disabled' and exits 0."""
    config_dir = tmp_path / "ws"
    config_dir.mkdir()
    (config_dir / ".booty.yml").write_text("schema_version: 1\ntest_command: pytest\n")

    runner = CliRunner()
    with patch("booty.cli.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(GITHUB_TOKEN="x")
        result = runner.invoke(
            cli, ["memory", "query", "--pr", "1", "--repo", "o/r", "--workspace", str(config_dir)], obj={}
        )
    assert result.exit_code == 0
    assert "Memory disabled" in result.output


@patch("github.Github")
def test_memory_query_pr_returns_matches(mock_github, monkeypatch, tmp_path):
    """With --pr and GITHUB_TOKEN, query returns formatted matches or (no related history)."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    config_dir = tmp_path / "ws"
    config_dir.mkdir()
    (config_dir / ".booty.yml").write_text(
        "schema_version: 1\ntest_command: pytest\nmemory:\n  enabled: true\n"
    )
    path = tmp_path / "memory.jsonl"
    now = datetime.now(timezone.utc)
    append_record(
        path,
        {
            "type": "incident",
            "timestamp": now.isoformat(),
            "summary": "DB timeout",
            "links": [{"url": "https://github.com/o/r/issues/1", "type": "github_issue"}],
            "id": "r1",
            "repo": "o/r",
            "paths": ["src/foo.py"],
        },
    )

    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_file = MagicMock()
    mock_file.filename = "src/foo.py"
    mock_pr.get_files.return_value = [mock_file]
    mock_gh = MagicMock()
    mock_gh.get_repo.return_value = mock_repo
    mock_repo.get_pull.return_value = mock_pr
    mock_github.return_value = mock_gh

    runner = CliRunner()
    with patch("booty.cli.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(GITHUB_TOKEN="token")
        result = runner.invoke(
            cli, ["memory", "query", "--pr", "1", "--repo", "o/r", "--workspace", str(config_dir)], obj={}
        )
    assert result.exit_code == 0
    assert "incident" in result.output
    assert "DB timeout" in result.output


@patch("github.Github")
def test_memory_query_json_output(mock_github, monkeypatch, tmp_path):
    """query --json outputs valid JSON list of matches."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    config_dir = tmp_path / "ws"
    config_dir.mkdir()
    (config_dir / ".booty.yml").write_text(
        "schema_version: 1\ntest_command: pytest\nmemory:\n  enabled: true\n"
    )

    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_file = MagicMock()
    mock_file.filename = "src/bar.py"
    mock_pr.get_files.return_value = [mock_file]
    mock_gh = MagicMock()
    mock_gh.get_repo.return_value = mock_repo
    mock_repo.get_pull.return_value = mock_pr
    mock_github.return_value = mock_gh

    runner = CliRunner()
    with patch("booty.cli.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(GITHUB_TOKEN="token")
        result = runner.invoke(
            cli,
            ["memory", "query", "--pr", "1", "--repo", "o/r", "--workspace", str(config_dir), "--json"],
            obj={},
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
