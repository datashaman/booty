"""Planner worker — consumes planner queue, produces minimal plan."""

from booty.logging import get_logger
from booty.planner.jobs import PlannerJob, planner_queue
from booty.planner.schema import HandoffToBuilder, Plan
from booty.planner.store import plan_path_for_issue, save_plan


def process_planner_job(job: PlannerJob) -> None:
    """Process planner job: build minimal plan, store to plans/owner/repo/issue.json."""
    logger = get_logger().bind(job_id=job.job_id, issue_number=job.issue_number)
    goal = job.payload.get("issue", {}).get("title", "Untitled") or "Untitled"
    handoff = HandoffToBuilder(
        branch_name_hint="plan",
        commit_message_hint=goal,
        pr_title=goal,
        pr_body_outline="",
    )
    plan = Plan(
        plan_version="1",
        goal=goal,
        steps=[],
        risk_level="LOW",
        touch_paths=[],
        handoff_to_builder=handoff,
    )
    path = plan_path_for_issue(job.owner, job.repo, job.issue_number)
    save_plan(plan, path)
    logger.info("planner_plan_stored", path=str(path))
