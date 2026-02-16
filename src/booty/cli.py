"""CLI entrypoint for Booty."""

import asyncio
import subprocess

import click

from booty.config import get_settings, verifier_enabled
from booty.test_runner.config import load_booty_config
from booty.test_runner.executor import execute_tests
from booty.github.checks import create_check_run


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
