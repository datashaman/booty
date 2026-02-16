"""Release Governor — Security override consumption (read, poll, prune)."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

OVERRIDE_TTL_DAYS = 14


def get_security_override(
    state_dir: Path,
    repo_full_name: str,
    sha: str,
) -> dict | None:
    """Load Security override for (repo_full_name, sha).

    Prunes entries with created_at older than 14 days on read.
    Returns override dict or None if not found.
    """
    path = state_dir / "security_overrides.json"
    if not path.exists():
        return None

    key = f"{repo_full_name}:{sha}"
    cutoff = datetime.now(timezone.utc) - timedelta(days=OVERRIDE_TTL_DAYS)

    # Acquire exclusive lock first, then read, prune, and write atomically
    with open(path, "r+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return None

            # Prune expired entries
            pruned = False
            for k, v in list(data.items()):
                created = v.get("created_at", "")
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt < cutoff:
                        del data[k]
                        pruned = True
                except (ValueError, TypeError):
                    pass

            # Write pruned data back atomically if changes were made
            if pruned:
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

            return data.get(key)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def get_security_override_with_poll(
    state_dir: Path,
    repo_full_name: str,
    sha: str,
    max_wait_sec: int | None = None,
    interval_sec: float = 5.0,
) -> dict | None:
    """Poll for Security override; returns when found or after max_wait_sec.

    Handles race: Governor may run before Security has written override.
    If max_wait_sec is 0 or None, checks once (no polling).
    """
    import os
    import time

    if max_wait_sec is None:
        max_wait_sec = int(os.environ.get("RELEASE_GOVERNOR_OVERRIDE_POLL_SEC", "120"))
    if max_wait_sec <= 0:
        return get_security_override(state_dir, repo_full_name, sha)

    deadline = time.monotonic() + max_wait_sec
    while True:
        ov = get_security_override(state_dir, repo_full_name, sha)
        if ov is not None:
            return ov
        if time.monotonic() >= deadline:
            return None
        time.sleep(interval_sec)
