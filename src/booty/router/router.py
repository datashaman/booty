"""Canonical event router: normalize → should_run → enqueue.

ROUTE-01 through ROUTE-05. Webhook delegates issues, pull_request, workflow_run here.
"""

import re
from datetime import datetime, timezone

from github import Github

from booty.architect.artifact import get_plan_for_builder
from booty.architect.config import apply_architect_env_overrides, get_architect_config
from booty.config import get_settings
from booty.github.comments import post_builder_blocked_comment, post_self_modification_disabled_comment
from booty.github.repo_config import load_booty_config_for_repo
from booty.jobs import Job
from booty.logging import get_logger
from booty.memory import add_record, get_memory_config
from booty.memory.adapters import (
    build_deploy_failure_record,
    build_governor_hold_record,
)
from booty.memory.config import apply_memory_env_overrides
from booty.planner.jobs import PlannerJob, planner_enqueue, planner_is_duplicate, planner_mark_processed
from booty.planner.store import get_plan_for_issue
from booty.release_governor.deploy import dispatch_deploy
from booty.release_governor.failure_issues import create_or_append_deploy_failure_issue
from booty.release_governor.handler import handle_workflow_run
from booty.release_governor.store import (
    append_deploy_to_history,
    get_state_dir,
    has_delivery_id,
    load_release_state,
    record_delivery_id,
    save_release_state,
)
from booty.release_governor.ux import post_allow_status, post_hold_status
from booty.router.events import IssueEvent, PREvent
from booty.router.normalizer import normalize
from booty.router.should_run import RoutingContext, should_run
from booty.self_modification.detector import is_self_modification
from booty.test_runner.config import (
    apply_release_governor_env_overrides,
    load_booty_config_from_content,
)
from booty.memory.surfacing import surface_governor_hold
from booty.reviewer import ReviewerJob
from booty.security import SecurityJob
from booty.verifier import VerifierJob

logger = get_logger()


async def route_github_event(
    event_type: str,
    payload: dict,
    delivery_id: str | None,
    app_state,
    *,
    background_tasks=None,
) -> dict:
    """Route GitHub webhook event: normalize, decide, enqueue.

    Returns dict with status (accepted|ignored|already_processed), reason?, job_id?, etc.
    """
    if event_type == "issues":
        return await _route_issues(payload, delivery_id, app_state)
    if event_type == "pull_request":
        return await _route_pull_request(payload, delivery_id, app_state)
    if event_type == "workflow_run":
        return await _route_workflow_run(
            payload, delivery_id, app_state, background_tasks=background_tasks
        )

    logger.info(
        "event_skip",
        agent=None,
        repo=None,
        event_type=event_type,
        reason="unsupported_event",
    )
    return {"status": "ignored", "reason": "unsupported_event"}


async def _route_issues(
    payload: dict, delivery_id: str | None, app_state
) -> dict:
    """Route issues events: planner | builder per routing rules."""
    settings = get_settings()
    internal = normalize("issues", payload, delivery_id)
    if internal is None or not isinstance(internal, IssueEvent):
        logger.info(
            "event_skip",
            agent=None,
            repo=None,
            event_type="issues",
            reason="normalize_failed",
        )
        return {"status": "ignored", "reason": "normalize_failed"}

    action = internal.action
    labels = internal.labels
    has_trigger_label = (
        (action == "opened" and settings.TRIGGER_LABEL in labels)
        or (
            action == "labeled"
            and payload.get("label", {}).get("name") == settings.TRIGGER_LABEL
        )
    )

    ctx: RoutingContext = {
        "repo_full_name": internal.full_name,
        "event_type": "issues",
        "action": action,
        "issue_number": internal.issue_number,
        "has_trigger_label": has_trigger_label,
    }

    booty_config = load_booty_config_for_repo(internal.repo_url, settings.GITHUB_TOKEN)
    job_queue = getattr(app_state, "job_queue", None)

    # Planner trigger
    if has_trigger_label and should_run("planner", internal.full_name, ctx, settings, booty_config):
        if delivery_id and planner_is_duplicate(delivery_id):
            return {"status": "already_processed"}
        job_id = f"planner-{internal.issue_number}-{delivery_id or 'no-delivery'}"
        job = PlannerJob(
            job_id=job_id,
            issue_number=internal.issue_number,
            issue_url=payload.get("issue", {}).get("html_url", ""),
            repo_url=internal.repo_url,
            owner=internal.owner,
            repo=internal.repo_name,
            payload=internal.raw_payload,
        )
        enqueued = await planner_enqueue(job)
        if not enqueued:
            logger.error("planner_enqueue_failed", job_id=job_id)
            return {"status": "error", "event": "planner", "reason": "enqueue_failed"}
        if delivery_id:
            planner_mark_processed(delivery_id)
        logger.info("planner_job_accepted", job_id=job_id, issue_number=internal.issue_number)
        return {"status": "accepted", "event": "planner", "job_id": job_id}

    # Builder trigger (requires plan)
    if not has_trigger_label:
        logger.info(
            "event_skip",
            agent="planner",
            repo=internal.full_name,
            event_type="issues",
            reason="not_plan_or_builder_trigger",
        )
        return {"status": "ignored", "reason": "not_plan_or_builder_trigger"}

    architect_config = get_architect_config(booty_config) if booty_config else None
    if architect_config:
        architect_config = apply_architect_env_overrides(architect_config)
    architect_enabled = architect_config is not None and architect_config.enabled

    plan, unreviewed = get_plan_for_builder(
        internal.owner, internal.repo_name, internal.issue_number,
        github_token=settings.GITHUB_TOKEN,
    )
    if architect_enabled and unreviewed:
        plan = None
    elif architect_enabled and plan is None:
        pass

    if plan is None:
        # Safety net: enqueue Planner
        if should_run("planner", internal.full_name, ctx, settings, booty_config):
            if delivery_id and planner_is_duplicate(delivery_id):
                return {"status": "already_processed"}
            job_id = f"planner-{internal.issue_number}-{delivery_id or 'no-delivery'}"
            planner_job = PlannerJob(
                job_id=job_id,
                issue_number=internal.issue_number,
                issue_url=payload.get("issue", {}).get("html_url", ""),
                repo_url=internal.repo_url,
                owner=internal.owner,
                repo=internal.repo_name,
                payload=internal.raw_payload,
            )
            enqueued = await planner_enqueue(planner_job)
            if enqueued:
                if delivery_id:
                    planner_mark_processed(delivery_id)
                logger.info(
                    "planner_enqueued_for_builder_safety_net",
                    issue_number=internal.issue_number,
                    job_id=job_id,
                )
                return {
                    "status": "accepted",
                    "event": "planner",
                    "reason": "builder_needs_plan",
                    "job_id": job_id,
                }
        if background_tasks:
            background_tasks.add_task(
                post_builder_blocked_comment,
                settings.GITHUB_TOKEN,
                internal.repo_url,
                internal.issue_number,
            )
        logger.info("builder_blocked_no_plan", issue_number=internal.issue_number)
        return {"status": "ignored", "reason": "builder_blocked_no_plan"}

    if not job_queue:
        return {"status": "ignored", "reason": "no_job_queue"}

    if delivery_id and job_queue.is_duplicate(delivery_id):
        return {"status": "already_processed"}
    if job_queue.has_issue_in_queue(internal.repo_url, internal.issue_number):
        return {"status": "already_processed"}

    is_self = is_self_modification(internal.repo_url, settings.BOOTY_OWN_REPO_URL)
    if is_self and not settings.BOOTY_SELF_MODIFY_ENABLED:
        if background_tasks:
            background_tasks.add_task(
                post_self_modification_disabled_comment,
                settings.GITHUB_TOKEN,
                internal.repo_url,
                internal.issue_number,
            )
        return {
            "status": "ignored",
            "reason": "self_modification_disabled",
            "issue_number": internal.issue_number,
        }

    if delivery_id:
        job_queue.mark_processed(delivery_id)

    issue = payload["issue"]
    job_id = f"{issue['number']}-{delivery_id}"
    job = Job(
        job_id=job_id,
        issue_url=issue["html_url"],
        issue_number=issue["number"],
        payload=internal.raw_payload,
        is_self_modification=is_self,
        repo_url=internal.repo_url,
    )
    enqueued = await job_queue.enqueue(job)
    if not enqueued:
        logger.error("enqueue_failed", job_id=job_id)
        return {"status": "error", "reason": "enqueue_failed"}
    logger.info("job_accepted", job_id=job_id, issue_number=issue["number"])
    return {"status": "accepted", "job_id": job_id}


async def _route_pull_request(
    payload: dict, delivery_id: str | None, app_state
) -> dict:
    """Route pull_request events: reviewer | verifier | security per config."""
    settings = get_settings()
    internal = normalize("pull_request", payload, delivery_id)
    if internal is None or not isinstance(internal, PREvent):
        logger.info(
            "event_skip",
            agent=None,
            repo=None,
            event_type="pull_request",
            reason="normalize_failed",
        )
        return {"status": "ignored", "reason": "normalize_failed"}

    if internal.action not in ("opened", "synchronize", "reopened"):
        logger.info(
            "event_skip",
            agent=None,
            repo=internal.full_name,
            event_type="pull_request",
            reason="unhandled_action",
        )
        return {"status": "ignored", "reason": "unhandled_action"}

    if not internal.head_sha:
        logger.warning("pull_request_missing_head_sha", pr_number=internal.pr_number)
        return {"status": "ignored", "reason": "missing_head_sha"}

    verifier_queue = getattr(app_state, "verifier_queue", None)
    security_queue = getattr(app_state, "security_queue", None)
    reviewer_queue = getattr(app_state, "reviewer_queue", None)
    booty_config = load_booty_config_for_repo(internal.repo_url, settings.GITHUB_TOKEN)

    ctx: RoutingContext = {
        "repo_full_name": internal.full_name,
        "event_type": "pull_request",
        "action": internal.action,
        "is_agent_pr": internal.is_agent_pr,
    }

    if not should_run("verifier", internal.full_name, ctx, settings, booty_config) and not should_run(
        "security", internal.full_name, ctx, settings, booty_config
    ) and not should_run("reviewer", internal.full_name, ctx, settings, booty_config):
        logger.info(
            "event_skip",
            agent=None,
            repo=internal.full_name,
            event_type="pull_request",
            reason="all_pr_agents_disabled",
        )
        return {"status": "ignored", "reason": "all_pr_agents_disabled"}

    verifier_enqueued = False
    verifier_job_id = None
    if verifier_queue and should_run("verifier", internal.full_name, ctx, settings, booty_config):
        if verifier_queue.is_duplicate(internal.pr_number, internal.head_sha):
            logger.info(
                "verifier_already_processed",
                pr_number=internal.pr_number,
                head_sha=internal.head_sha[:7],
            )
        else:
            issue_number_from_branch = None
            branch_match = re.match(r"^agent/issue-(\d+)$", internal.head_ref)
            if branch_match:
                issue_number_from_branch = int(branch_match.group(1))
            verifier_job_id = f"verifier-{internal.pr_number}-{internal.head_sha[:7]}"
            job = VerifierJob(
                job_id=verifier_job_id,
                owner=internal.owner,
                repo_name=internal.repo_name,
                pr_number=internal.pr_number,
                head_sha=internal.head_sha,
                head_ref=internal.head_ref,
                repo_url=internal.repo_url,
                installation_id=internal.installation_id,
                payload=internal.raw_payload,
                is_agent_pr=internal.is_agent_pr,
                issue_number=issue_number_from_branch,
            )
            if await verifier_queue.enqueue(job):
                verifier_enqueued = True
                logger.info("verifier_job_accepted", job_id=verifier_job_id, pr_number=internal.pr_number)
            else:
                logger.error("verifier_enqueue_failed", job_id=verifier_job_id)

    reviewer_enqueued = False
    reviewer_job_id = None
    if reviewer_queue and should_run("reviewer", internal.full_name, ctx, settings, booty_config):
        if not reviewer_queue.is_duplicate(internal.full_name, internal.pr_number, internal.head_sha):
            reviewer_job_id = f"reviewer-{internal.pr_number}-{internal.head_sha[:7]}"
            reviewer_job = ReviewerJob(
                job_id=reviewer_job_id,
                owner=internal.owner,
                repo_name=internal.repo_name,
                pr_number=internal.pr_number,
                head_sha=internal.head_sha,
                head_ref=internal.head_ref,
                repo_url=internal.repo_url,
                installation_id=internal.installation_id,
                payload=internal.raw_payload,
                is_agent_pr=True,
            )
            if await reviewer_queue.enqueue(reviewer_job):
                reviewer_enqueued = True
                logger.info("reviewer_job_accepted", job_id=reviewer_job_id, pr_number=internal.pr_number)
            else:
                logger.error("reviewer_enqueue_failed", job_id=reviewer_job_id)

    security_enqueued = False
    security_job_id = None
    if security_queue and should_run("security", internal.full_name, ctx, settings, booty_config):
        if not security_queue.is_duplicate(internal.pr_number, internal.head_sha):
            security_job_id = f"security-{internal.pr_number}-{internal.head_sha[:7]}"
            base = payload.get("pull_request", {}).get("base", {})
            base_sha = base.get("sha", "") or ""
            base_ref = base.get("ref", "") or "main"
            sec_job = SecurityJob(
                job_id=security_job_id,
                owner=internal.owner,
                repo_name=internal.repo_name,
                pr_number=internal.pr_number,
                head_sha=internal.head_sha,
                head_ref=internal.head_ref,
                base_sha=base_sha,
                base_ref=base_ref,
                repo_url=internal.repo_url,
                installation_id=internal.installation_id,
                payload=internal.raw_payload,
            )
            if await security_queue.enqueue(sec_job):
                security_enqueued = True
                logger.info("security_job_accepted", job_id=security_job_id, pr_number=internal.pr_number)
            else:
                logger.error("security_enqueue_failed", job_id=security_job_id)

    if verifier_enqueued or security_enqueued or reviewer_enqueued:
        job_id = verifier_job_id or security_job_id or reviewer_job_id
        return {"status": "accepted", "job_id": job_id}

    return {"status": "already_processed"}


async def _route_workflow_run(
    payload: dict, delivery_id: str | None, app_state, *, background_tasks=None
) -> dict:
    """Route workflow_run events: governor.evaluate | governor.observe_deploy."""
    settings = get_settings()
    internal = normalize("workflow_run", payload, delivery_id)
    if internal is None:
        logger.info(
            "event_skip",
            agent=None,
            repo=None,
            event_type="workflow_run",
            reason="normalize_failed",
        )
        return {"status": "ignored", "reason": "normalize_failed"}

    if internal.action != "completed":
        logger.info(
            "event_skip",
            agent="governor",
            repo=internal.full_name,
            event_type="workflow_run",
            reason="workflow_not_completed",
        )
        return {"status": "ignored", "reason": "workflow_not_completed"}

    wr = payload.get("workflow_run", {})
    workflow_name = internal.workflow_name
    workflow_path = internal.workflow_path
    head_sha = internal.head_sha
    head_branch = internal.head_branch
    conclusion = internal.conclusion
    repo_full_name = internal.full_name
    repo = payload.get("repository", {})

    booty_config = None
    try:
        gh = Github(settings.GITHUB_TOKEN)
        gh_repo = gh.get_repo(repo_full_name)
        default_branch = gh_repo.default_branch or "main"
        fc = gh_repo.get_contents(".booty.yml", ref=default_branch)
        yaml_content = fc.decoded_content.decode("utf-8")
        config = load_booty_config_from_content(yaml_content)
        booty_config = config
        governor_config = apply_release_governor_env_overrides(
            config.release_governor
        ) if getattr(config, "release_governor", None) else None
    except Exception:
        governor_config = None

    ctx: RoutingContext = {
        "repo_full_name": repo_full_name,
        "event_type": "workflow_run",
        "action": internal.action,
    }
    if not should_run("governor", repo_full_name, ctx, settings, booty_config):
        logger.info(
            "event_skip",
            agent="governor",
            repo=repo_full_name,
            event_type="workflow_run",
            reason="governor_disabled",
        )
        return {"status": "ignored", "reason": "governor_disabled"}

    is_deploy = (
        (workflow_path or "").endswith(governor_config.deploy_workflow_name)
        or workflow_name == governor_config.deploy_workflow_name
    )
    is_verification = workflow_name == governor_config.verification_workflow_name

    if is_deploy:
        state_dir = get_state_dir()
        wr_id = wr.get("id") or wr.get("run_id") or ""
        deploy_run_key = f"deploy_run_{wr_id}" if wr_id else f"deploy_run_{head_sha}"
        if has_delivery_id(state_dir, repo_full_name, deploy_run_key):
            return {"status": "already_processed"}

        now_iso = datetime.now(timezone.utc).isoformat()
        state = load_release_state(state_dir)
        if conclusion == "success":
            state.production_sha_previous = state.production_sha_current
            state.production_sha_current = head_sha
            state.last_deploy_attempt_sha = head_sha
            state.last_deploy_time = now_iso
            state.last_deploy_result = "success"
            save_release_state(state_dir, state)
            append_deploy_to_history(state_dir, head_sha, now_iso, "success")
        elif conclusion in ("failure", "cancelled"):
            failure_type = (
                "deploy:cancelled" if conclusion == "cancelled"
                else "deploy:health-check-failed"
            )
            run_url = wr.get("html_url", "") or wr.get("url", "") or ""
            create_or_append_deploy_failure_issue(
                gh_repo, head_sha, run_url, conclusion, failure_type
            )
            mem_config = get_memory_config(config) if config else None
            if mem_config:
                mem_config = apply_memory_env_overrides(mem_config)
            if mem_config and mem_config.enabled:
                try:
                    record = build_deploy_failure_record(
                        head_sha, run_url, conclusion, failure_type, repo_full_name
                    )
                    add_record(record, mem_config)
                except Exception as e:
                    logger.warning(
                        "memory_ingestion_failed",
                        type="deploy_failure",
                        error=str(e),
                    )
            state.last_deploy_attempt_sha = head_sha
            state.last_deploy_time = now_iso
            state.last_deploy_result = "failure"
            save_release_state(state_dir, state)
            append_deploy_to_history(state_dir, head_sha, now_iso, "failure")
        else:
            state.last_deploy_attempt_sha = head_sha
            state.last_deploy_time = now_iso
            state.last_deploy_result = conclusion or "skipped"
            save_release_state(state_dir, state)
            append_deploy_to_history(state_dir, head_sha, now_iso, conclusion or "skipped")

        if delivery_id:
            record_delivery_id(state_dir, repo_full_name, deploy_run_key, delivery_id)

        logger.info(
            "governor_deploy_outcome_processed",
            repo=repo_full_name,
            head_sha=head_sha[:7] if head_sha else "?",
            conclusion=conclusion,
        )
        return {
            "status": "accepted",
            "event": "workflow_run",
            "type": "deploy_outcome",
            "conclusion": conclusion,
        }

    if is_verification and conclusion == "success" and head_branch == "main":
        state_dir = get_state_dir()
        if has_delivery_id(state_dir, repo_full_name, head_sha):
            return {"status": "already_processed"}

        decision = handle_workflow_run(payload, governor_config)

        html_url = repo.get("html_url", "") or ""
        actions_url = f"{html_url.rstrip('/')}/actions" if html_url else ""
        hold_docs_url = (
            f"{html_url.rstrip('/')}/blob/{default_branch}/docs/release-governor.md"
            if html_url else ""
        )

        if decision.outcome == "ALLOW":
            dispatch_deploy(gh_repo, governor_config, head_sha)
            now_iso = datetime.now(timezone.utc).isoformat()
            state = load_release_state(state_dir)
            state.last_deploy_attempt_sha = head_sha
            state.last_deploy_time = now_iso
            state.last_deploy_result = "pending"
            save_release_state(state_dir, state)
            append_deploy_to_history(state_dir, head_sha, now_iso, "pending")
            post_allow_status(gh_repo, head_sha, actions_url)
        else:
            approval_hint = None
            if decision.reason == "high_risk_no_approval":
                mode = governor_config.approval_mode
                if mode == "label" and governor_config.approval_label:
                    approval_hint = f"Approval via label: {governor_config.approval_label}"
                elif mode == "comment" and governor_config.approval_command:
                    approval_hint = f"Approval via comment: {governor_config.approval_command}"
                elif mode == "environment":
                    approval_hint = "Approval via env: RELEASE_GOVERNOR_APPROVED=true"
            post_hold_status(gh_repo, head_sha, decision, hold_docs_url, approval_hint)
            mem_config = get_memory_config(config) if config else None
            if mem_config:
                mem_config = apply_memory_env_overrides(mem_config)
            if mem_config and mem_config.enabled and mem_config.comment_on_pr and background_tasks:
                background_tasks.add_task(
                    surface_governor_hold,
                    settings.GITHUB_TOKEN,
                    repo_full_name,
                    head_sha,
                    decision.reason,
                    mem_config,
                )
            if mem_config and mem_config.enabled:
                try:
                    record = build_governor_hold_record(decision, repo_full_name)
                    add_record(record, mem_config)
                except Exception as e:
                    logger.warning(
                        "memory_ingestion_failed",
                        type="governor_hold",
                        error=str(e),
                    )

        if delivery_id:
            record_delivery_id(state_dir, repo_full_name, head_sha, delivery_id)

        logger.info(
            "governor_workflow_processed",
            repo=repo_full_name,
            head_sha=head_sha[:7],
            outcome=decision.outcome,
            reason=decision.reason,
        )
        return {"status": "accepted", "event": "workflow_run", "outcome": decision.outcome}

    logger.info(
        "event_skip",
        agent="governor",
        repo=repo_full_name,
        event_type="workflow_run",
        reason="workflow_not_matched",
    )
    return {"status": "ignored", "reason": "workflow_not_matched"}
