"""Planner storage — plan paths and atomic JSON write."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from booty.planner.schema import Plan


def get_planner_state_dir() -> Path:
    """Return planner state directory. Precedence: PLANNER_STATE_DIR env, $HOME/.booty/state, ./.booty/state."""
    if path := os.environ.get("PLANNER_STATE_DIR"):
        p = Path(path).expanduser()
    elif home := os.environ.get("HOME"):
        p = Path(home) / ".booty" / "state"
    else:
        p = Path.cwd() / ".booty" / "state"
    p.mkdir(parents=True, exist_ok=True)
    return p


def plan_path_for_issue(
    owner: str, repo: str, issue_number: int, state_dir: Path | None = None
) -> Path:
    """Return path for issue-based plan: state_dir/plans/owner/repo/{issue_number}.json."""
    sd = state_dir or get_planner_state_dir()
    return sd / "plans" / owner / repo / f"{issue_number}.json"


def plan_path_for_ad_hoc(text: str, state_dir: Path | None = None) -> Path:
    """Return path for ad-hoc plan: state_dir/plans/ad-hoc-{timestamp}-{short_hash}.json."""
    from datetime import datetime, timezone

    sd = state_dir or get_planner_state_dir()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    short_hash = hashlib.sha256(text.encode()).hexdigest()[:8]
    return sd / "plans" / f"ad-hoc-{ts}-{short_hash}.json"


def plan_path_for_ad_hoc_from_input(
    input_hash_val: str, state_dir: Path | None = None
) -> Path:
    """Return path for ad-hoc plan: state_dir/plans/ad-hoc/ad-hoc-{timestamp}-{input_hash[:8]}.json."""
    from datetime import datetime, timezone

    sd = state_dir or get_planner_state_dir()
    ad_hoc_dir = sd / "plans" / "ad-hoc"
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond:06d}"
    short_hash = input_hash_val[:8]
    return ad_hoc_dir / f"ad-hoc-{ts}-{short_hash}.json"


def save_plan(plan: Plan | dict, path: Path) -> None:
    """Write plan to path atomically. Creates parent dirs."""
    if isinstance(plan, Plan):
        data = plan.model_dump()
    else:
        data = plan

    path.parent.mkdir(parents=True, exist_ok=True)

    fd = tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    )
    try:
        json.dump(data, fd, indent=2, default=str)
        fd.flush()
        os.fsync(fd.fileno())
        fd.close()
        os.replace(fd.name, path)
    except Exception:
        if os.path.exists(fd.name):
            os.unlink(fd.name)
        raise


def load_plan(path: Path) -> Plan | None:
    """Load plan from path. Returns None if file missing or invalid."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return Plan.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return None
