"""Architect review — force re-evaluation for CLI (ARCH-30)."""

from booty.architect.config import ArchitectConfig, apply_architect_env_overrides, get_architect_config
from booty.architect.input import ArchitectInput
from booty.architect.output import ArchitectPlan, build_architect_plan
from booty.architect.worker import process_architect_input
from booty.planner.generation import generate_plan
from booty.planner.input import get_repo_context, normalize_github_issue
from booty.planner.risk import classify_risk_from_paths


def force_architect_review(
    owner: str,
    repo: str,
    issue_number: int,
    token: str,
    architect_config: ArchitectConfig | None = None,
) -> tuple[str, ArchitectPlan | None, str | None]:
    """Force Architect re-evaluation of an issue. Bypasses cache.

    Returns (outcome, architect_plan, block_reason).
    outcome: "approved" | "rewritten" | "blocked"
    architect_plan: None when blocked
    block_reason: reason string when blocked, else None
    """
    from github import Github

    g = Github(token)
    gh_repo = g.get_repo(f"{owner}/{repo}")
    issue = gh_repo.get_issue(issue_number)
    issue_dict = {
        "title": issue.title,
        "body": issue.body or "",
        "labels": [{"name": l.name} for l in issue.get_labels()],
        "html_url": issue.html_url,
        "number": issue.number,
    }
    repo_info = {"owner": owner, "repo": repo}
    repo_context = get_repo_context(owner, repo, token)
    inp = normalize_github_issue(issue_dict, repo_info, repo_context)
    plan = generate_plan(inp)
    risk_level, _ = classify_risk_from_paths(plan.touch_paths)
    plan = plan.model_copy(update={"risk_level": risk_level})
    if architect_config:
        config = apply_architect_env_overrides(architect_config)
    else:
        config = ArchitectConfig()
    arch_inp = ArchitectInput(
        plan=plan,
        normalized_input=inp,
        repo_context=repo_context,
        issue_metadata={"issue_number": issue_number},
    )
    result = process_architect_input(config, arch_inp)
    if result.approved:
        architect_plan = build_architect_plan(result.plan, result.architect_notes)
        notes = (result.architect_notes or "").lower()
        outcome = "rewritten" if ("ambiguous" in notes or "overreach" in notes) else "approved"
        return (outcome, architect_plan, None)
    reason = ""
    if result.architect_notes and "(" in result.architect_notes and ")" in result.architect_notes:
        start = result.architect_notes.rfind("(") + 1
        end = result.architect_notes.rfind(")")
        if end > start:
            reason = result.architect_notes[start:end]
    return ("blocked", None, reason or None)
