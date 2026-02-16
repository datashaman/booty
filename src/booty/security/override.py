"""Security override persistence — risk overrides for Governor consumption."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from booty.release_governor.store import get_state_dir


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON to temp file, fsync, then atomic rename."""
    fd = tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    )
    try:
        json.dump(data, fd, indent=2)
        fd.flush()
        os.fsync(fd.fileno())
        fd.close()
        os.replace(fd.name, path)
    except Exception:
        if os.path.exists(fd.name):
            os.unlink(fd.name)
        raise


def persist_override(repo_full_name: str, sha: str, paths: list[str]) -> None:
    """Persist risk override for (repo_full_name, sha) for Governor to consume.

    Key: "{repo_full_name}:{sha}"
    Payload: risk_override=HIGH, reason=permission_surface_change, sha, paths, created_at.
    Appends/merges into security_overrides.json with atomic write + LOCK_EX.
    """
    state_dir = get_state_dir()
    path = state_dir / "security_overrides.json"
    key = f"{repo_full_name}:{sha}"
    entry = {
        "risk_override": "HIGH",
        "reason": "permission_surface_change",
        "sha": sha,
        "paths": paths,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    data: dict = {}
    if path.exists():
        with open(path) as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    data[key] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)

    with open(path, "r") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            _atomic_write_json(path, data)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
