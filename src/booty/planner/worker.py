"""Planner worker — consumes planner queue, produces minimal plan."""

from booty.config import get_settings
from booty.logging import get_logger
from booty.planner.input import get_repo_context, normalize_from_job
from booty.planner.jobs import PlannerJob, planner_queue
from booty.planner.schema import HandoffToBuilder, Plan
from booty.planner.store import plan_path_for_issue, save_plan


def process_planner_job(job: PlannerJob) -> None:
    """Process planner job: build minimal plan, store to plans/owner/repo/issue.json."""
    logger = get_logger().bind(job_id=job.job_id, issue_number=job.issue_number)
    repo_context = None
    if job.owner and job.repo:
        token = get_settings().GITHUB_TOKEN or ""
        if token.strip():
            repo_context = get_repo_context(job.owner, job.repo, token)
    inp = normalize_from_job(job, repo_context=repo_context)
    goal = inp.goal
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
