"""PR promotion: draft → ready-for-review when validation passes."""

from github import GithubException
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from booty.github.comments import _get_repo
from booty.logging import get_logger

logger = get_logger()


def _should_retry_promotion(exc: BaseException) -> bool:
    """Retry only on 5xx, network errors; never on 4xx (auth, not found)."""
    if isinstance(exc, GithubException):
        status = getattr(exc, "status", None)
        return status is None or (status is not None and status >= 500)
    return isinstance(exc, (ConnectionError, TimeoutError, OSError))


@retry(
    retry=retry_if_exception(_should_retry_promotion),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
def promote_to_ready_for_review(
    github_token: str, repo_url: str, pr_number: int
) -> None:
    """Mark a draft PR as ready for review via GitHub GraphQL mutation.

    Uses PyGithub's mark_ready_for_review() which wraps the
    markPullRequestReadyForReview GraphQL mutation. Retries on 5xx/network
    errors; does not retry on 4xx (auth, not found). On final failure after
    retries, raises the exception (caller should post failure comment).

    Args:
        github_token: GitHub authentication token
        repo_url: Repository URL (e.g., https://github.com/owner/repo)
        pr_number: PR number to promote

    Raises:
        GithubException: If promotion fails after retries (4xx or final 5xx)
        ConnectionError | TimeoutError | OSError: If network fails after retries
    """
    repo = _get_repo(github_token, repo_url)
    pr = repo.get_pull(pr_number)
    pr.mark_ready_for_review()
    logger.info("pr_promoted", pr_number=pr_number)
