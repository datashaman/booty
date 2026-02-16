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
