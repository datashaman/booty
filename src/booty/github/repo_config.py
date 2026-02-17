"""Load BootyConfig from a repo's .booty.yml via GitHub API."""

from urllib.parse import urlparse

from github import Github

from booty.logging import get_logger
from booty.test_runner.config import load_booty_config_from_content

logger = get_logger()


def repo_from_url(repo_url: str) -> str:
    """Parse owner/repo from GitHub URL (https://github.com/o/r or git@github.com:o/r.git)."""
    if not repo_url:
        return ""
    if repo_url.startswith("git@"):
        part = repo_url.split(":")[-1].rstrip("/").removesuffix(".git")
        return part
    parsed = urlparse(repo_url)
    path = (parsed.path or "").lstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path


def load_booty_config_for_repo(repo_url: str, gh_token: str):
    """Load BootyConfig from repo .booty.yml. Returns None on any error."""
    try:
        owner_repo = repo_from_url(repo_url)
        if not owner_repo or "/" not in owner_repo:
            return None
        g = Github(gh_token)
        repo = g.get_repo(owner_repo)
        fc = repo.get_contents(".booty.yml", ref=repo.default_branch or "main")
        content = fc.decoded_content.decode("utf-8")
        return load_booty_config_from_content(content)
    except Exception as e:
        logger.warning("booty_config_load_failed", repo_url=repo_url, error=str(e))
        return None
