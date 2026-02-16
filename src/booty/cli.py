"""CLI entrypoint for Booty."""

import asyncio
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import click

from booty.config import get_settings, verifier_enabled
from booty.release_governor import is_governor_enabled
from booty.release_governor.deploy import dispatch_deploy
from booty.release_governor.handler import simulate_decision_for_cli
from booty.release_governor.store import (
    append_deploy_to_history,
    get_state_dir,
    load_release_state,
    save_release_state,
)
from booty.test_runner.config import (
    apply_release_governor_env_overrides,
    load_booty_config,
    load_booty_config_from_content,
)
from booty.test_runner.executor import execute_tests
from booty.github.checks import create_check_run


def _infer_repo_from_git(workspace: Path) -> str | None:
    """Infer owner/repo from git remote origin. Returns None if not a git repo."""
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None
        url = r.stdout.strip()
        # git@github.com:owner/repo.git or https://github.com/owner/repo.git
        m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
        if m:
            return f"{m.group(1)}/{m.group(2).removesuffix('.git')}"
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _unblock_hints(reason: str, config) -> list[str]:
    """Build unblock hint bullets from decision reason and config."""
    if reason in ("high_risk_no_approval", "first_deploy_required"):
        mode = getattr(config, "approval_mode", "environment")
        label = getattr(config, "approval_label", None) or "release:approved"
        cmd = getattr(config, "approval_command", None) or "/approve"
        hints = []
        if mode == "environment":
            hints.append("Set RELEASE_GOVERNOR_APPROVED=true")
        if mode == "label":
            hints.append(f"Add label {label!r} to PR")
        if mode == "comment":
            hints.append(f"Comment {cmd!r} on PR")
        if not hints:
            hints.append("Set RELEASE_GOVERNOR_APPROVED=true")
        return hints
    if reason == "deploy_not_configured":
        return ["Configure deploy_workflow_name in .booty.yml release_governor"]
    if reason == "degraded_high_risk":
        return ["Wait for degraded state to clear"]
    if reason == "cooldown":
        return [f"Wait {getattr(config, 'cooldown_minutes', 30)} minutes after last failure"]
    if reason == "rate_limit":
        return [f"Max {getattr(config, 'max_deploys_per_hour', 6)} deploys/hour; wait"]
    return ["See docs/release-governor.md for troubleshooting"]


def main() -> None:
    """Booty CLI entrypoint."""
    cli(auto_envvar_prefix="BOOTY")


@click.group()
def cli() -> None:
    """Booty — self-managing builder agent."""


@cli.command()
def status() -> None:
    """Print verifier and configuration status."""
    try:
        settings = get_settings()
    except Exception:
        import os
        app_id = os.environ.get("GITHUB_APP_ID", "")
        app_key = os.environ.get("GITHUB_APP_PRIVATE_KEY", "")
        if app_id and app_key:
            click.echo("verifier: enabled (incomplete config for other commands)")
        else:
            click.echo("verifier: disabled (missing GITHUB_APP_ID or GITHUB_APP_PRIVATE_KEY)")
        return
    if verifier_enabled(settings):
        click.echo("verifier: enabled")
    else:
        click.echo("verifier: disabled (missing GITHUB_APP_ID or GITHUB_APP_PRIVATE_KEY)")


@cli.group()
def memory() -> None:
    """Memory (event storage) commands."""


@memory.command("status")
@click.option("--workspace", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output")
def memory_status(workspace: str, as_json: bool) -> None:
    """Show memory state (enabled, record count, retention)."""
    from booty.memory.config import apply_memory_env_overrides, get_memory_config
    from booty.memory.lookup import within_retention
    from booty.memory.store import get_memory_state_dir, read_records

    ws = Path(workspace).resolve()
    try:
        config = load_booty_config(ws)
    except Exception:
        click.echo("Memory disabled")
        raise SystemExit(0)
    mem_config = get_memory_config(config) if config else None
    if not mem_config:
        click.echo("Memory disabled")
        raise SystemExit(0)
    mem_config = apply_memory_env_overrides(mem_config)
    if not mem_config.enabled:
        click.echo("Memory disabled")
        raise SystemExit(0)
    state_dir = get_memory_state_dir()
    path = state_dir / "memory.jsonl"
    records = read_records(path)
    filtered = [r for r in records if within_retention(r, mem_config.retention_days)]
    count = len(filtered)
    if as_json:
        click.echo(json.dumps({"enabled": True, "records": count, "retention_days": mem_config.retention_days}))
        return
    click.echo("enabled: true")
    click.echo(f"records: {count}")
    click.echo(f"retention_days: {mem_config.retention_days}")


@memory.command("query")
@click.option("--pr", type=int, help="PR number to query files from")
@click.option("--sha", type=str, help="Commit SHA (resolves to PR for paths)")
@click.option("--repo", help="Repository owner/repo (required when cannot infer from git)")
@click.option("--workspace", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output")
def memory_query(
    pr: int | None,
    sha: str | None,
    repo: str | None,
    workspace: str,
    as_json: bool,
) -> None:
    """Query memory by PR or commit SHA."""
    from booty.memory import query as memory_query_fn
    from booty.memory.config import apply_memory_env_overrides, get_memory_config
    from booty.memory.surfacing import format_matches_for_pr
    from booty.memory.store import get_memory_state_dir

    if (pr is not None and sha is not None) or (pr is None and sha is None):
        raise click.UsageError("Provide exactly one of --pr or --sha")
    ws = Path(workspace).resolve()
    repo_name = repo or _infer_repo_from_git(ws)
    if not repo_name:
        click.echo("Use --repo owner/repo", err=True)
        raise SystemExit(1)
    token = get_settings().GITHUB_TOKEN or ""
    if not token.strip():
        click.echo("GITHUB_TOKEN required", err=True)
        raise SystemExit(1)
    try:
        config = load_booty_config(ws)
    except Exception:
        click.echo("Memory disabled")
        raise SystemExit(0)
    mem_config = get_memory_config(config) if config else None
    if not mem_config:
        click.echo("Memory disabled")
        raise SystemExit(0)
    mem_config = apply_memory_env_overrides(mem_config)
    if not mem_config.enabled:
        click.echo("Memory disabled")
        raise SystemExit(0)
    try:
        from github import Github

        g = Github(token)
        gh_repo = g.get_repo(repo_name)
        if pr is not None:
            pull = gh_repo.get_pull(pr)
            paths = [f.filename for f in pull.get_files()]
        else:
            commit = gh_repo.get_commit(sha)
            pulls = list(commit.get_pulls())
            if not pulls:
                click.echo("No PR found for sha", err=True)
                raise SystemExit(1)
            pull = pulls[0]
            paths = [f.filename for f in pull.get_files()]
        state_dir = get_memory_state_dir()
        matches = memory_query_fn(
            paths=paths,
            repo=repo_name,
            config=mem_config,
            state_dir=state_dir,
        )
    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    if as_json:
        click.echo(json.dumps(matches, default=str))
        return
    formatted = format_matches_for_pr(matches)
    if formatted:
        click.echo(formatted)
    else:
        click.echo("(no related history)")


@memory.group()
def ingest() -> None:
    """Ingest records from external sources."""


@ingest.command("revert")
@click.option("--repo", required=True, help="Repository in owner/repo format")
@click.option("--sha", required=True, help="Merge/revert commit SHA")
@click.option("--reverted-sha", "reverted_sha", required=True, help="SHA being reverted")
def ingest_revert(repo: str, sha: str, reverted_sha: str) -> None:
    """Store a revert record in Memory (requires .booty.yml memory.enabled)."""
    if "/" not in repo:
        raise click.BadParameter("--repo must be in owner/repo format", param_hint="repo")
    settings = get_settings()
    token = settings.GITHUB_TOKEN or ""
    if not token or not token.strip():
        click.echo("GITHUB_TOKEN required", err=True)
        raise SystemExit(1)
    try:
        from github import Github

        g = Github(token)
        gh_repo = g.get_repo(repo)
        fc = gh_repo.get_contents(".booty.yml", ref=gh_repo.default_branch or "main")
        config = load_booty_config_from_content(fc.decoded_content.decode())
    except Exception as e:
        click.echo(f"Cannot load .booty.yml: {e}", err=True)
        raise SystemExit(1)
    from booty.memory import add_record, get_memory_config
    from booty.memory.adapters import build_revert_record
    from booty.memory.config import apply_memory_env_overrides

    mem_config = get_memory_config(config) if config else None
    if mem_config:
        mem_config = apply_memory_env_overrides(mem_config)
    if not mem_config or not mem_config.enabled:
        click.echo("Memory disabled")
        raise SystemExit(0)
    record = build_revert_record(repo, sha, reverted_sha, source="cli")
    result = add_record(record, mem_config)
    if result.get("added"):
        click.echo("Added")
    else:
        click.echo("Duplicate")


@cli.group()
def governor() -> None:
    """Release Governor commands."""


@governor.command("status")
@click.option("--workspace", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output")
def governor_status(workspace: str, as_json: bool) -> None:
    """Show release state when Governor enabled."""
    ws = Path(workspace).resolve()
    try:
        config = load_booty_config(ws)
    except Exception:
        click.echo("Governor: disabled")
        return
    if not is_governor_enabled(config):
        click.echo("Governor: disabled")
        return
    state_dir = get_state_dir()
    state = load_release_state(state_dir)
    if as_json:
        click.echo(
            json.dumps(
                {
                    "governor": "enabled",
                    "production_sha_current": state.production_sha_current,
                    "production_sha_previous": state.production_sha_previous,
                    "last_deploy_attempt_sha": state.last_deploy_attempt_sha,
                    "last_deploy_time": state.last_deploy_time,
                    "last_deploy_result": state.last_deploy_result,
                    "last_health_check": state.last_health_check,
                }
            )
        )
        return
    click.echo("Governor: enabled")
    click.echo(f"  production_sha_current: {state.production_sha_current or '(none)'}")
    click.echo(f"  production_sha_previous: {state.production_sha_previous or '(none)'}")
    click.echo(f"  last_deploy_attempt_sha: {state.last_deploy_attempt_sha or '(none)'}")
    click.echo(f"  last_deploy_time: {state.last_deploy_time or '(none)'}")
    click.echo(f"  last_deploy_result: {state.last_deploy_result}")
    click.echo(f"  last_health_check: {state.last_health_check or '(none)'}")


def _governor_sha_option(f):
    """Add --sha and optional positional sha to a command."""
    f = click.option("--sha", "sha_opt", help="Commit SHA to evaluate")(
        click.argument("sha_pos", required=False)(f)
    )
    return f


@governor.command("simulate")
@click.option("--repo", help="Repository owner/repo (default: infer from git remote)")
@click.option("--workspace", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--show-paths", is_flag=True, help="Include paths that drove risk")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output")
@_governor_sha_option
def governor_simulate(
    sha_pos: str | None,
    sha_opt: str | None,
    repo: str | None,
    workspace: str,
    show_paths: bool,
    as_json: bool,
) -> None:
    """Dry-run decision for a SHA (no deploy)."""
    sha = sha_opt or sha_pos
    if not sha:
        raise click.UsageError("Provide SHA: booty governor simulate <sha> or --sha <sha>")
    ws = Path(workspace).resolve()
    try:
        config = load_booty_config(ws)
    except Exception:
        click.echo("Governor: disabled (no valid .booty.yml)", err=True)
        raise SystemExit(1)
    if not is_governor_enabled(config):
        click.echo("Governor: disabled", err=True)
        raise SystemExit(1)
    repo_name = repo or _infer_repo_from_git(ws)
    if not repo_name:
        click.echo("Cannot infer repo. Use --repo owner/repo", err=True)
        raise SystemExit(1)
    gov_config = apply_release_governor_env_overrides(config.release_governor)
    try:
        decision, risk_paths = simulate_decision_for_cli(repo_name, sha, gov_config, ws)
    except ValueError as e:
        if "GITHUB_TOKEN" in str(e):
            click.echo("GITHUB_TOKEN required for simulate; set it to fetch diff", err=True)
            raise SystemExit(1)
        raise
    if as_json:
        out = {
            "decision": decision.outcome,
            "risk_class": decision.risk_class,
            "reason": decision.reason,
            "sha": decision.sha,
        }
        if decision.outcome == "HOLD":
            out["unblock_hints"] = _unblock_hints(decision.reason, gov_config)
        if show_paths:
            out["paths"] = risk_paths
        click.echo(json.dumps(out))
        return
    click.echo(f"decision: {decision.outcome}")
    click.echo(f"risk_class: {decision.risk_class}")
    click.echo(f"reason: {decision.reason}")
    click.echo(f"sha: {decision.sha}")
    if decision.outcome == "HOLD":
        for h in _unblock_hints(decision.reason, gov_config):
            click.echo(f"unblock: {h}")
    if show_paths and risk_paths:
        click.echo("paths:")
        for p in risk_paths:
            click.echo(f"  {p}")


@governor.command("trigger")
@click.option("--repo", help="Repository owner/repo (default: infer from git remote)")
@click.option("--workspace", type=click.Path(exists=True, file_okay=False), default=".")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output")
@_governor_sha_option
def governor_trigger(
    sha_pos: str | None,
    sha_opt: str | None,
    repo: str | None,
    workspace: str,
    as_json: bool,
) -> None:
    """Manually trigger deploy when decision is ALLOW; exit 1 on HOLD."""
    sha = sha_opt or sha_pos
    if not sha:
        raise click.UsageError("Provide SHA: booty governor trigger <sha> or --sha <sha>")
    ws = Path(workspace).resolve()
    try:
        config = load_booty_config(ws)
    except Exception:
        click.echo("Governor: disabled (no valid .booty.yml)", err=True)
        raise SystemExit(1)
    if not is_governor_enabled(config):
        click.echo("Governor: disabled", err=True)
        raise SystemExit(1)
    repo_name = repo or _infer_repo_from_git(ws)
    if not repo_name:
        click.echo("Cannot infer repo. Use --repo owner/repo", err=True)
        raise SystemExit(1)
    gov_config = apply_release_governor_env_overrides(config.release_governor)
    try:
        decision, _ = simulate_decision_for_cli(repo_name, sha, gov_config, ws)
    except ValueError as e:
        if "GITHUB_TOKEN" in str(e):
            click.echo("GITHUB_TOKEN required for trigger; set it to fetch diff", err=True)
            raise SystemExit(1)
        raise
    if decision.outcome == "HOLD":
        if as_json:
            click.echo(
                json.dumps(
                    {
                        "decision": "HOLD",
                        "reason": decision.reason,
                        "risk_class": decision.risk_class,
                        "sha": decision.sha,
                        "unblock_hints": _unblock_hints(decision.reason, gov_config),
                    }
                )
            )
        else:
            click.echo(f"decision: {decision.outcome}")
            click.echo(f"reason: {decision.reason}")
            for h in _unblock_hints(decision.reason, gov_config):
                click.echo(f"unblock: {h}")
        raise SystemExit(1)
    # ALLOW — dispatch deploy
    token = get_settings().GITHUB_TOKEN
    if not token or not token.strip():
        click.echo("GITHUB_TOKEN required for trigger", err=True)
        raise SystemExit(1)
    from github import Github
    gh = Github(token)
    gh_repo = gh.get_repo(repo_name)
    dispatch_deploy(gh_repo, gov_config, sha)
    now = datetime.now(timezone.utc).isoformat()
    state_dir = get_state_dir()
    state = load_release_state(state_dir)
    state.last_deploy_attempt_sha = sha
    state.last_deploy_time = now
    state.last_deploy_result = "pending"
    save_release_state(state_dir, state)
    append_deploy_to_history(state_dir, sha, now, "pending")
    owner, repo_slug = repo_name.split("/", 1)
    actions_url = f"https://github.com/{owner}/{repo_slug}/actions"
    if as_json:
        click.echo(
            json.dumps(
                {
                    "decision": "ALLOW",
                    "triggered": True,
                    "sha": sha,
                    "timestamp": now,
                    "actions_url": actions_url,
                }
            )
        )
    else:
        click.echo(f"Triggered: deploy workflow dispatched for {sha}")
        click.echo(f"  timestamp: {now}")
        click.echo(f"  Actions: {actions_url}")


@cli.group()
def plan() -> None:
    """Plan generation subcommands."""


@plan.command("issue")
@click.option("--repo", help="Repository owner/repo (default: infer from git)")
@click.option("--verbose", is_flag=True, help="Show progress and details")
@click.option("--output", "output_path", help="Also write plan to this path")
@click.argument("issue_number", type=int)
def plan_issue(issue_number: int, repo: str | None, verbose: bool, output_path: str | None) -> None:
    """Generate plan from GitHub issue. Requires GITHUB_TOKEN."""
    from booty.planner.generation import generate_plan
    from booty.planner.input import get_repo_context, normalize_github_issue
    from booty.planner.risk import classify_risk_from_paths
    from booty.planner.store import plan_path_for_issue, save_plan

    settings = get_settings()
    token = settings.GITHUB_TOKEN or ""
    if not token or not token.strip():
        click.echo("Error: GITHUB_TOKEN required", err=True)
        raise SystemExit(1)

    ws = Path.cwd()
    repo_name = repo or _infer_repo_from_git(ws)
    if not repo_name or "/" not in repo_name:
        click.echo("Error: Cannot infer repo. Use --repo owner/repo", err=True)
        raise SystemExit(1)

    try:
        from github import Github

        g = Github(token)
        gh_repo = g.get_repo(repo_name)
        issue = gh_repo.get_issue(issue_number)
        issue_dict = {
            "title": issue.title,
            "body": issue.body or "",
            "labels": [{"name": l.name} for l in issue.get_labels()],
            "html_url": issue.html_url,
            "number": issue.number,
        }
        owner, repo_slug = repo_name.split("/", 1)
        repo_info = {"owner": owner, "repo": repo_slug}
        repo_context = get_repo_context(owner, repo_slug, token) if token else None
        inp = normalize_github_issue(issue_dict, repo_info, repo_context)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc(file=__import__("sys").stderr)
        raise SystemExit(1)

    plan_obj = generate_plan(inp)
    risk_level, _ = classify_risk_from_paths(plan_obj.touch_paths)
    plan_obj = plan_obj.model_copy(update={"risk_level": risk_level})
    path = plan_path_for_issue(owner, repo_slug, issue_number)
    save_plan(plan_obj, path)

    repo_url = f"https://github.com/{repo_name}"
    try:
        from github import GithubException

        from booty.github.comments import post_plan_comment
        from booty.logging import get_logger
        from booty.planner.output import format_plan_comment

        body = format_plan_comment(plan_obj)
        post_plan_comment(token, repo_url, issue_number, body)
    except GithubException as e:
        get_logger().warning(
            "plan_comment_post_failed",
            issue_number=issue_number,
            error=str(e),
        )

    if output_path:
        import shutil
        shutil.copy(path, output_path)

    goal_snippet = f"{plan_obj.goal[:50]}{'...' if len(plan_obj.goal) > 50 else ''}"
    click.echo(f"{path} | {goal_snippet} | {len(plan_obj.steps)} steps | {risk_level}")


@plan.command("text")
@click.option("--repo", help="Repository owner/repo (default: infer from git when in repo)")
@click.option("--verbose", is_flag=True, help="Show progress and details")
@click.option("--output", "output_path", help="Also write plan to this path")
@click.argument("text", required=True)
def plan_text(text: str, repo: str | None, verbose: bool, output_path: str | None) -> None:
    """Generate plan from free text prompt."""
    from booty.planner.generation import generate_plan
    from booty.planner.input import get_repo_context, normalize_cli_text
    from booty.planner.risk import classify_risk_from_paths
    from booty.planner.store import plan_path_for_ad_hoc, save_plan

    ws = Path.cwd()
    repo_info = None
    if repo and "/" in repo:
        owner, repo_slug = repo.split("/", 1)
        repo_info = {"owner": owner, "repo": repo_slug}
    else:
        inferred = _infer_repo_from_git(ws)
        if inferred and "/" in inferred:
            owner, repo_slug = inferred.split("/", 1)
            repo_info = {"owner": owner, "repo": repo_slug}

    token = get_settings().GITHUB_TOKEN or ""
    repo_context = (
        get_repo_context(repo_info["owner"], repo_info["repo"], token)
        if repo_info and token.strip()
        else None
    )
    inp = normalize_cli_text(text, repo_info=repo_info, repo_context=repo_context)
    plan_obj = generate_plan(inp)
    risk_level, _ = classify_risk_from_paths(plan_obj.touch_paths)
    plan_obj = plan_obj.model_copy(update={"risk_level": risk_level})
    path = plan_path_for_ad_hoc(text)
    save_plan(plan_obj, path)

    if output_path:
        import shutil
        shutil.copy(path, output_path)

    goal_snippet = f"{plan_obj.goal[:50]}{'...' if len(plan_obj.goal) > 50 else ''}"
    click.echo(f"{path} | {goal_snippet} | {len(plan_obj.steps)} steps | {risk_level}")


@cli.group()
def verifier() -> None:
    """Verifier (GitHub Checks) commands."""


@verifier.command("run")
@click.option(
    "--workspace",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Workspace directory with .booty.yml",
)
def verifier_run(workspace: str) -> None:
    """Run tests per .booty.yml (setup, install, test)."""
    from pathlib import Path

    ws = Path(workspace).resolve()
    config = load_booty_config(ws)
    setup = getattr(config, "setup_command", None) if config else None
    install = getattr(config, "install_command", None) if config else None
    if setup:
        click.echo(f"Running setup: {setup}")
        r = subprocess.run(setup, shell=True, cwd=ws)
        if r.returncode != 0:
            raise SystemExit(r.returncode or 1)
    if install:
        click.echo(f"Running install: {install}")
        r = subprocess.run(install, shell=True, cwd=ws)
        if r.returncode != 0:
            raise SystemExit(r.returncode or 1)
    timeout = getattr(config, "timeout", None) or getattr(config, "timeout_seconds", 300)
    result = asyncio.run(execute_tests(config.test_command, timeout, ws))
    if result.stdout:
        click.echo(result.stdout)
    if result.stderr:
        click.echo(result.stderr, err=True)
    raise SystemExit(result.exit_code if result.exit_code >= 0 else 1)


@verifier.command("check-test")
@click.option("--repo", required=True, help="Repository in owner/repo format")
@click.option("--sha", required=True, help="Commit SHA to create check run on")
@click.option("--installation-id", "installation_id", required=True, type=int, help="GitHub App installation ID")
@click.option("--details-url", help="URL for check run details")
@click.option("--dry-run", is_flag=True, help="Validate inputs only, don't create check run")
def check_test(
    repo: str,
    sha: str,
    installation_id: int,
    details_url: str | None,
    dry_run: bool,
) -> None:
    """Create a test check run (booty/verifier) on a commit."""
    if "/" not in repo:
        raise click.BadParameter("--repo must be in owner/repo format", param_hint="repo")
    owner, repo_name = repo.split("/", 1)

    if dry_run:
        click.echo(f"dry-run: repo={repo} sha={sha} installation_id={installation_id}")
        return

    settings = get_settings()
    output = {"title": "Booty Verifier", "summary": "Manual check-test"}
    check_run = create_check_run(
        owner,
        repo_name,
        sha,
        installation_id,
        settings,
        status="queued",
        output=output,
        details_url=details_url,
    )

    if check_run is None:
        click.echo("verifier: disabled — set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY", err=True)
        raise SystemExit(1)

    click.echo(f"check_run_id={check_run.id}")
    click.echo(f"installation_id={installation_id}")
    click.echo(f"repo={repo}")
    click.echo(f"sha={sha}")
    click.echo(f"status={check_run.status}")
    url = getattr(check_run, "html_url", None) or getattr(check_run, "url", "")
    click.echo(f"url={url}")


if __name__ == "__main__":
    main()
