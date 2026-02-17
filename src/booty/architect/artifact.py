"""Architect artifact — persist ArchitectPlan for Builder consumption (ARCH-26)."""

import json
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from booty.architect.output import ArchitectPlan
from booty.planner.schema import HandoffToBuilder, Plan, Step
from booty.planner.store import get_planner_state_dir, get_plan_for_issue


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


def load_architect_plan_for_issue(
    owner: str,
    repo: str,
    issue_number: int,
    state_dir: Path | None = None,
) -> ArchitectPlan | None:
    """Load ArchitectPlan from artifact path. Returns None if missing or invalid."""
    path = architect_artifact_path(owner, repo, issue_number, state_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    try:
        steps_raw = data.get("steps") or []
        steps = [Step.model_validate(s) for s in steps_raw]
        handoff_raw = data.get("handoff_to_builder")
        if not handoff_raw:
            return None
        handoff = HandoffToBuilder.model_validate(handoff_raw)
        return ArchitectPlan(
            plan_version=str(data.get("plan_version", "1")),
            goal=data.get("goal", ""),
            steps=steps,
            touch_paths=data.get("touch_paths") or [],
            risk_level=data.get("risk_level", "LOW"),
            handoff_to_builder=handoff,
            architect_notes=data.get("architect_notes"),
        )
    except (ValidationError, TypeError, KeyError):
        return None


def get_plan_for_builder(
    owner: str,
    repo: str,
    issue_number: int,
    github_token: str | None = None,
    state_dir: Path | None = None,
) -> tuple[Plan | None, bool]:
    """Resolve plan for Builder: Architect artifact first, then Planner plan.

    Returns (plan, unreviewed) where unreviewed=True means Planner plan without Architect review.
    """
    ap = load_architect_plan_for_issue(owner, repo, issue_number, state_dir)
    if ap is not None:
        plan = Plan(
            goal=ap.goal,
            steps=ap.steps,
            handoff_to_builder=ap.handoff_to_builder,
            touch_paths=ap.touch_paths,
            risk_level=ap.risk_level,
            plan_version="1",
            assumptions=[],
            constraints=[],
            tests=[],
            rollback=[],
            metadata={"source": "architect"},
        )
        return (plan, False)
    plan = get_plan_for_issue(owner, repo, issue_number, github_token, state_dir)
    if plan is not None:
        return (plan, True)
    return (None, False)
