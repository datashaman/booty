"""GitHub Checks API integration via GitHub App auth."""

from typing import TYPE_CHECKING, Any

from github import Auth, GithubException, GithubIntegration

from booty.config import Settings, verifier_enabled
from booty.logging import get_logger

if TYPE_CHECKING:
    from github import CheckRun, Repository

logger = get_logger()


def get_verifier_repo(
    owner: str,
    repo_name: str,
    installation_id: int,
    settings: Settings,
) -> "Repository | None":
    """Get Repository instance authenticated via GitHub App for installation.

    Returns None if Verifier is disabled (missing credentials) or on auth failure.
    """
    if not verifier_enabled(settings):
        return None

    pk = (
        settings.GITHUB_APP_PRIVATE_KEY.replace("\\n", "\n")
        if settings.GITHUB_APP_PRIVATE_KEY
        else ""
    )
    try:
        auth = Auth.AppAuth(
            app_id=int(settings.GITHUB_APP_ID),
            private_key=pk,
        )
        gi = GithubIntegration(auth=auth)
        g = gi.get_github_for_installation(installation_id)
        return g.get_repo(f"{owner}/{repo_name}")
    except (GithubException, ValueError) as e:
        reason = "auth_failed"
        if "key" in str(e).lower() or "pem" in str(e).lower():
            reason = "bad_key"
        elif "jwt" in str(e).lower() or "token" in str(e).lower():
            reason = "jwt_failed"
        logger.error(
            "verifier_auth_failed",
            reason=reason,
            owner=owner,
            repo=repo_name,
            error=str(e),
        )
        return None


def create_check_run(
    owner: str,
    repo_name: str,
    head_sha: str,
    installation_id: int,
    settings: Settings,
    *,
    status: str = "queued",
    output: dict[str, Any] | None = None,
    details_url: str | None = None,
) -> "CheckRun | None":
    """Create a booty/verifier check run on a commit.

    Returns None if Verifier is disabled. Uses GitHub App auth only.
    """
    repo = get_verifier_repo(owner, repo_name, installation_id, settings)
    if repo is None:
        return None

    output = output or {"title": "Booty Verifier", "summary": "Queued"}
    kwargs: dict[str, Any] = {
        "name": "booty/verifier",
        "head_sha": head_sha,
        "status": status,
        "output": output,
    }
    if details_url is not None:
        kwargs["details_url"] = details_url

    return repo.create_check_run(**kwargs)


def edit_check_run(
    check_run: "CheckRun",
    *,
    status: str | None = None,
    conclusion: str | None = None,
    output: dict[str, Any] | None = None,
) -> "CheckRun":
    """Update check run status, conclusion, or output.

    Used for queued → in_progress → completed lifecycle transitions.
    Only non-None kwargs are passed to check_run.edit().
    """
    kwargs: dict[str, Any] = {}
    if status is not None:
        kwargs["status"] = status
    if conclusion is not None:
        kwargs["conclusion"] = conclusion
    if output is not None:
        kwargs["output"] = output
    return check_run.edit(**kwargs)
