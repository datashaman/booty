"""Tests for memory store — append_record, read_records, get_memory_state_dir."""

import os
from pathlib import Path

import pytest

from booty.memory.store import append_record, get_memory_state_dir, read_records


def test_get_memory_state_dir_uses_env(tmp_path):
    """get_memory_state_dir uses MEMORY_STATE_DIR when set."""
    os.environ["MEMORY_STATE_DIR"] = str(tmp_path)
    try:
        state_dir = get_memory_state_dir()
        assert state_dir == tmp_path
    finally:
        os.environ.pop("MEMORY_STATE_DIR", None)


def test_append_record_persists_and_read_records_returns(monkeypatch, tmp_path):
    """append_record persists record; read_records returns it."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    path = tmp_path / "memory.jsonl"
    append_record(path, {"type": "test", "id": "x"})
    recs = read_records(path)
    assert len(recs) == 1
    assert recs[0]["type"] == "test"
    assert recs[0]["id"] == "x"


def test_read_records_skips_partial_last_line(tmp_path):
    """read_records skips partial last line (truncated JSON)."""
    path = tmp_path / "memory.jsonl"
    path.write_text('{"type":"a"}\n{"type":"b"}\n{"incomplete"\n')
    recs = read_records(path)
    assert len(recs) == 2
    assert recs[0]["type"] == "a"
    assert recs[1]["type"] == "b"


def test_append_record_creates_dir_if_missing(tmp_path):
    """append_record creates dir if missing."""
    subdir = tmp_path / "nested" / "state"
    path = subdir / "memory.jsonl"
    assert not subdir.exists()
    append_record(path, {"type": "test"})
    assert subdir.exists()
    assert path.exists()
    recs = read_records(path)
    assert len(recs) == 1


def test_multiple_appends_yield_multiple_records_in_order(monkeypatch, tmp_path):
    """Multiple appends yield multiple records in order."""
    monkeypatch.setenv("MEMORY_STATE_DIR", str(tmp_path))
    path = tmp_path / "memory.jsonl"
    append_record(path, {"type": "first", "n": 1})
    append_record(path, {"type": "second", "n": 2})
    append_record(path, {"type": "third", "n": 3})
    recs = read_records(path)
    assert len(recs) == 3
    assert recs[0]["n"] == 1
    assert recs[1]["n"] == 2
    assert recs[2]["n"] == 3
