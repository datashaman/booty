"""Deploy failure issue creation (GOV-17)."""

from datetime import datetime, timedelta, timezone

from booty.logging import get_logger

logger = get_logger()

APPEND_WINDOW_MINUTES = 30


def create_or_append_deploy_failure_issue(
    gh_repo,
    sha: str,
    run_url: str,
    conclusion: str,
    failure_type: str = "deploy:unknown",
) -> int | None:
    """Create or append deploy failure issue (GOV-17).

    Creates issue with labels deploy-failure, severity:high, failure_type.
    If same SHA failed in last 30 min, appends comment to existing issue.

    Returns:
        Issue number on success, None on error.
    """
    sha_short = sha[:7] if sha else "?"
    labels = ["deploy-failure", "severity:high", failure_type]
    title = f"Deploy failure: {sha_short}"
    now_iso = datetime.now(timezone.utc).isoformat()
    body = f"**SHA:** {sha}\n**Run:** {run_url}\n**Conclusion:** {conclusion}\n**Time:** {now_iso}"

    try:
        # Check for recent same-SHA issue to append to
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=APPEND_WINDOW_MINUTES)
        cutoff_str = cutoff.isoformat()

        open_issues = gh_repo.get_issues(
            state="open",
            labels=labels[:1],  # deploy-failure only for search
        )
        for issue in open_issues:
            if sha_short not in (issue.title or ""):
                continue
            created = getattr(issue, "created_at", None)
            if created and created.isoformat() < cutoff_str:
                continue
            # Append comment
            comment_body = f"**Retry failure** — {now_iso}\n**Run:** {run_url}\n**Conclusion:** {conclusion}"
            issue.create_comment(comment_body)
            logger.info(
                "deploy_failure_appended",
                issue_number=issue.number,
                sha=sha_short,
            )
            return issue.number
    except Exception as e:
        logger.warning("deploy_failure_append_check_failed", error=str(e))

    try:
        issue = gh_repo.create_issue(title=title, body=body, labels=labels)
        logger.info("deploy_failure_issue_created", issue_number=issue.number, sha=sha_short)
        return issue.number
    except Exception as e:
        logger.error("deploy_failure_issue_create_failed", sha=sha_short, error=str(e))
        return None
