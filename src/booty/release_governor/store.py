"""Release state store and delivery ID cache. Atomic writes, single-writer safe."""

import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReleaseState:
    """Release state persisted to release.json."""

    production_sha_current: str | None = None
    production_sha_previous: str | None = None
    last_deploy_attempt_sha: str | None = None
    last_deploy_time: str | None = None  # ISO8601
    last_deploy_result: str = "pending"  # success|failure|pending
    last_health_check: str | None = None  # ISO8601
    deploy_history: list[dict] = field(default_factory=list)  # [{sha, time_iso8601, result}]; max 24


def get_state_dir() -> Path:
    """Return state directory. Create if missing. Precedence: env, $HOME/.booty/state, ./.booty/state."""
    if path := os.environ.get("RELEASE_GOVERNOR_STATE_DIR"):
        p = Path(path)
    elif home := os.environ.get("HOME"):
        p = Path(home) / ".booty" / "state"
    else:
        p = Path.cwd() / ".booty" / "state"
    p.mkdir(parents=True, exist_ok=True)
    return p


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
        if fd and os.path.exists(fd.name):
            os.unlink(fd.name)
        raise


def _state_to_dict(s: ReleaseState) -> dict:
    return {
        "production_sha_current": s.production_sha_current,
        "production_sha_previous": s.production_sha_previous,
        "last_deploy_attempt_sha": s.last_deploy_attempt_sha,
        "last_deploy_time": s.last_deploy_time,
        "last_deploy_result": s.last_deploy_result,
        "last_health_check": s.last_health_check,
        "deploy_history": s.deploy_history,
    }


def _dict_to_state(d: dict) -> ReleaseState:
    return ReleaseState(
        production_sha_current=d.get("production_sha_current"),
        production_sha_previous=d.get("production_sha_previous"),
        last_deploy_attempt_sha=d.get("last_deploy_attempt_sha"),
        last_deploy_time=d.get("last_deploy_time"),
        last_deploy_result=d.get("last_deploy_result", "pending"),
        last_health_check=d.get("last_health_check"),
        deploy_history=d.get("deploy_history") or [],
    )


def load_release_state(state_dir: Path) -> ReleaseState:
    """Load release state. Returns defaults if release.json missing. LOCK_SH for read."""
    path = state_dir / "release.json"
    if not path.exists():
        return ReleaseState()
    with open(path) as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            data = json.load(f)
            return _dict_to_state(data)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def save_release_state(state_dir: Path, state: ReleaseState) -> None:
    """Save release state. LOCK_EX, atomic write."""
    path = state_dir / "release.json"
    path.touch(exist_ok=True)
    with open(path, "r") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            _atomic_write_json(path, _state_to_dict(state))
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def has_delivery_id(state_dir: Path, repo: str, head_sha: str) -> bool:
    """Check if (repo, head_sha) has a delivery ID recorded."""
    path = state_dir / "delivery_ids.json"
    if not path.exists():
        return False
    key = f"{repo}:{head_sha}"
    with open(path) as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            data = json.load(f)
            return key in data
        except (json.JSONDecodeError, FileNotFoundError):
            return False
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


DEPLOY_HISTORY_MAX = 24


def append_deploy_to_history(
    state_dir: Path, sha: str, time_iso8601: str, result: str
) -> None:
    """Append deploy to history. Evict oldest if over DEPLOY_HISTORY_MAX."""
    state = load_release_state(state_dir)
    state.deploy_history.append({"sha": sha, "time_iso8601": time_iso8601, "result": result})
    while len(state.deploy_history) > DEPLOY_HISTORY_MAX:
        state.deploy_history.pop(0)
    save_release_state(state_dir, state)


def get_deploys_in_last_hour(state_dir: Path) -> int:
    """Return count of deploys in the last 60 minutes."""
    state = load_release_state(state_dir)
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - 3600
    count = 0
    for entry in state.deploy_history:
        ts_str = entry.get("time_iso8601", "")
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if dt.timestamp() >= cutoff:
                count += 1
        except (ValueError, TypeError):
            pass
    return count


def record_delivery_id(
    state_dir: Path, repo: str, head_sha: str, delivery_id: str
) -> None:
    """Record delivery ID for (repo, head_sha). Atomic write, LOCK_EX."""
    path = state_dir / "delivery_ids.json"
    key = f"{repo}:{head_sha}"
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
    data[key] = delivery_id
    path.touch(exist_ok=True)
    with open(path, "r") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            _atomic_write_json(path, data)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
