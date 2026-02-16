"""Planner worker — consumes planner queue, produces LLM-generated plan with risk."""

from booty.config import get_settings
from booty.logging import get_logger
from booty.planner.generation import generate_plan
from booty.planner.input import get_repo_context, normalize_from_job
from booty.planner.jobs import PlannerJob
from booty.planner.risk import classify_risk_from_paths
from booty.planner.store import plan_path_for_issue, save_plan


def process_planner_job(job: PlannerJob) -> None:
    """Process planner job: generate plan via LLM, classify risk, store to plans/."""
    logger = get_logger().bind(job_id=job.job_id, issue_number=job.issue_number)
    repo_context = None
    if job.owner and job.repo:
        token = get_settings().GITHUB_TOKEN or ""
        if token.strip():
            repo_context = get_repo_context(job.owner, job.repo, token)
    inp = normalize_from_job(job, repo_context=repo_context)
    plan = generate_plan(inp)
    risk_level, _ = classify_risk_from_paths(plan.touch_paths)
    plan = plan.model_copy(update={"risk_level": risk_level})
    path = plan_path_for_issue(job.owner, job.repo, job.issue_number)
    save_plan(plan, path)
    logger.info("planner_plan_stored", path=str(path), risk_level=risk_level)
