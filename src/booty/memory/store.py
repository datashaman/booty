"""Memory store — append-only memory.jsonl with durable writes."""

import fcntl
import json
import os
from pathlib import Path


def get_memory_state_dir() -> Path:
    """Return memory state directory. Precedence: MEMORY_STATE_DIR env, $HOME/.booty/state, ./.booty/state."""
    if path := os.environ.get("MEMORY_STATE_DIR"):
        p = Path(path)
    elif home := os.environ.get("HOME"):
        p = Path(home) / ".booty" / "state"
    else:
        p = Path.cwd() / ".booty" / "state"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _memory_jsonl_path(state_dir: Path) -> Path:
    """Return path to memory.jsonl in state dir."""
    return state_dir / "memory.jsonl"


def append_record(path: Path, record: dict) -> None:
    """Append record to memory.jsonl. Atomic append with fsync. Creates parent dir if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            line = json.dumps(record, default=str) + "\n"
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def read_records(path: Path) -> list[dict]:
    """Read records from memory.jsonl. Skips partial last line on JSONDecodeError."""
    if not path.exists():
        return []
    records: list[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                # Partial last line — skip
                pass
    return records
