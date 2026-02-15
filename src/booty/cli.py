"""CLI entrypoint for Booty."""

import click

from booty.config import get_settings, verifier_enabled
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
