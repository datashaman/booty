"""Deploy workflow dispatch (GOV-14, GOV-18)."""

from booty.config import get_settings
from booty.test_runner.config import ReleaseGovernorConfig


def dispatch_deploy(gh_repo, config: ReleaseGovernorConfig, head_sha: str) -> None:
    """Dispatch deploy workflow via workflow_dispatch with sha input (GOV-14, GOV-18).

    Uses GITHUB_TOKEN from get_settings(). Raises on failure; no return value.
    Never deploys non-head_sha — caller must pass exact head_sha from payload.
    """
    _ = get_settings().GITHUB_TOKEN  # Ensure token configured
    workflow = gh_repo.get_workflow(config.deploy_workflow_name)
    workflow.create_dispatch(
        ref=config.deploy_workflow_ref,
        inputs={"sha": head_sha},
    )
