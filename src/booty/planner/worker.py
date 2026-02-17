"""Planner worker — consumes planner queue, produces LLM-generated plan with risk."""

import os
from datetime import datetime, timezone

from github import Auth, Github, GithubException

from booty.config import get_settings
from booty.github.comments import post_plan_comment
from booty.test_runner.config import load_booty_config_from_content
from booty.logging import get_logger
from booty.planner.cache import (
    find_cached_issue_plan,
    input_hash,
    plan_hash,
)
from booty.planner.generation import generate_plan
from booty.planner.input import PlannerInput, get_repo_context, normalize_from_job
from booty.planner.jobs import PlannerJob, PlannerJobResult
from booty.planner.output import format_plan_comment
from booty.planner.risk import classify_risk_from_paths
from booty.planner.schema import Plan
from booty.planner.store import plan_path_for_issue, save_plan
from booty.operator.last_run import record_agent_completed
from booty.verifier.limits import limits_config_from_booty_config, format_limits_for_prompt


def process_planner_job(job: PlannerJob) -> PlannerJobResult:
    """Process planner job: generate plan via LLM, classify risk, store to plans/."""
    logger = get_logger().bind(job_id=job.job_id, issue_number=job.issue_number)
    repo_context = None
    booty_config = None
    if job.owner and job.repo:
        token = get_settings().GITHUB_TOKEN or ""
        if token.strip():
            repo_context = get_repo_context(job.owner, job.repo, token)
            try:
                gh = Github(auth=Auth.Token(token))
                gh_repo = gh.get_repo(f"{job.owner}/{job.repo}")
                default_branch = gh_repo.default_branch or "main"
                fc = gh_repo.get_contents(".booty.yml", ref=default_branch)
                yaml_content = fc.decoded_content.decode("utf-8")
                booty_config = load_booty_config_from_content(yaml_content)
            except Exception:
                booty_config = None
    limits = limits_config_from_booty_config(booty_config)
    limits_constraint = format_limits_for_prompt(limits)
    inp = normalize_from_job(job, repo_context=repo_context)
    h = input_hash(inp)
    ttl = float(os.environ.get("PLANNER_CACHE_TTL_HOURS", "24"))
    cached = find_cached_issue_plan(job.owner, job.repo, job.issue_number, h, ttl)
    cache_hit = cached is not None
    if cached:
        plan = cached
        logger.info("planner_cache_hit", job_id=job.job_id, issue_number=job.issue_number)
    else:
        plan = generate_plan(inp, limits_constraint=limits_constraint)
        risk_level, _ = classify_risk_from_paths(plan.touch_paths)
        plan = plan.model_copy(update={"risk_level": risk_level})
    new_metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_hash": h,
        "plan_hash": plan_hash(plan),
    }
    merged = plan.metadata | new_metadata
    plan = plan.model_copy(update={"metadata": merged})
    path = plan_path_for_issue(job.owner, job.repo, job.issue_number)
    save_plan(plan, path)
    logger.info("planner_plan_stored", path=str(path), risk_level=plan.risk_level)

    token = get_settings().GITHUB_TOKEN or ""
    if token.strip() and job.repo_url:
        try:
            body = format_plan_comment(plan)
            post_plan_comment(token, job.repo_url, job.issue_number, body)
            logger.info("planner_plan_posted", issue_number=job.issue_number)
        except GithubException as e:
            logger.error(
                "planner_comment_post_failed",
                issue_number=job.issue_number,
                error=str(e),
                status=e.status,
            )
    else:
        logger.warning(
            "planner_comment_skipped",
            issue_number=job.issue_number,
            reason="no token or repo_url",
        )

    record_agent_completed("planner")
    return PlannerJobResult(
        cache_hit=cache_hit,
        plan=plan,
        normalized_input=inp,
        repo_context=repo_context,
        job=job,
    )
