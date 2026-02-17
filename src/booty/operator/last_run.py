"""Last-run completion timestamps per agent (OPS-03)."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from booty.planner.store import get_planner_state_dir

AGENTS = ("verifier", "security", "reviewer", "planner", "architect", "builder")


def _last_run_path(state_dir: Path | None = None) -> Path:
    """Path to last_run.json: state_dir/operator/last_run.json."""
    sd = state_dir or get_planner_state_dir()
    return sd / "operator" / "last_run.json"


def record_agent_completed(agent: str) -> None:
    """Record agent completion with current UTC timestamp. Thread-safe for single-process."""
    path = _last_run_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, TypeError):
            pass
    data[agent] = datetime.now(timezone.utc).isoformat()
    fd = tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    )
    try:
        json.dump(data, fd, indent=0, separators=(",", ":"))
        fd.flush()
        os.fsync(fd.fileno())
        fd.close()
        os.replace(fd.name, path)
    except Exception:
        if os.path.exists(fd.name):
            os.unlink(fd.name)
        raise


def get_last_run(agent: str) -> str | None:
    """Return ISO-8601 UTC timestamp for agent's last completion, or None."""
    path = _last_run_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data.get(agent)
    except (json.JSONDecodeError, TypeError, KeyError):
        return None
