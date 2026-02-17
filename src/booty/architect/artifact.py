"""Architect artifact — persist ArchitectPlan for Builder consumption (ARCH-26)."""

import json
import os
import tempfile
from pathlib import Path

from booty.architect.output import ArchitectPlan
from booty.planner.store import get_planner_state_dir


def architect_artifact_path(
    owner: str,
    repo: str,
    issue_number: int,
    state_dir: Path | None = None,
) -> Path:
    """Return path for ArchitectPlan artifact: state_dir/plans/owner/repo/{issue}-architect.json."""
    sd = state_dir or get_planner_state_dir()
    return sd / "plans" / owner / repo / f"{issue_number}-architect.json"


def _architect_plan_to_dict(architect_plan: ArchitectPlan) -> dict:
    """Serialize ArchitectPlan to dict for JSON storage."""
    steps_data = [
        s.model_dump() if hasattr(s, "model_dump") else s
        for s in architect_plan.steps
    ]
    h = architect_plan.handoff_to_builder
    handoff_data = h.model_dump() if hasattr(h, "model_dump") else h
    return {
        "plan_version": architect_plan.plan_version,
        "goal": architect_plan.goal,
        "steps": steps_data,
        "touch_paths": architect_plan.touch_paths,
        "risk_level": architect_plan.risk_level,
        "handoff_to_builder": handoff_data,
        "architect_notes": architect_plan.architect_notes,
    }


def save_architect_artifact(
    owner: str,
    repo: str,
    issue_number: int,
    architect_plan: ArchitectPlan,
    state_dir: Path | None = None,
    input_hash: str | None = None,
) -> Path:
    """Persist ArchitectPlan to plans/owner/repo/{issue}-architect.json atomically."""
    path = architect_artifact_path(owner, repo, issue_number, state_dir)
    data = _architect_plan_to_dict(architect_plan)
    if input_hash is not None:
        data["input_hash"] = input_hash

    path.parent.mkdir(parents=True, exist_ok=True)
    fd = tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    )
    try:
        json.dump(data, fd, indent=0, separators=(",", ":"), default=str)
        fd.flush()
        os.fsync(fd.fileno())
        fd.close()
        os.replace(fd.name, path)
    except Exception:
        if os.path.exists(fd.name):
            os.unlink(fd.name)
        raise
    return path
