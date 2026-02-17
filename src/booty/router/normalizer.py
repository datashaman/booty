"""GitHub payload → internal event conversion.

Single entry point for GitHub → internal conversion before routing.
ROUTE-01: normalizer converts payloads to typed events before enqueue.
"""

from booty.config import get_settings
from booty.router.events import IssueEvent, PREvent, WorkflowRunEvent


def _sender_from_payload(payload: dict) -> str | None:
    """Extract sender login from payload if present."""
    sender = payload.get("sender", {})
    if isinstance(sender, dict):
        return sender.get("login") or None
    return getattr(sender, "login", None) or None


def normalize_issue_event(
    payload: dict, delivery_id: str | None
) -> IssueEvent | None:
    """Convert issues webhook payload to IssueEvent. Returns None if missing required fields."""
    action = payload.get("action")
    issue = payload.get("issue", {})
    repo = payload.get("repository", {})
    if not action or not issue or not repo:
        return None

    owner = repo.get("owner", {})
    if isinstance(owner, dict):
        owner_login = owner.get("login", "")
    else:
        owner_login = getattr(owner, "login", "") or ""

    repo_name = repo.get("name", "")
    full_name = repo.get("full_name", "")
    if not full_name and owner_login and repo_name:
        full_name = f"{owner_login}/{repo_name}"

    issue_number = issue.get("number", 0)
    labels_data = issue.get("labels", [])
    labels = [l.get("name", "") for l in labels_data] if isinstance(labels_data, list) else []

    repo_url = repo.get("html_url", "")
    if not repo_url and full_name:
        repo_url = f"https://github.com/{full_name}"

    return IssueEvent(
        action=str(action),
        delivery_id=delivery_id,
        sender=_sender_from_payload(payload),
        owner=owner_login,
        repo_name=repo_name,
        full_name=full_name,
        issue_number=issue_number,
        labels=labels,
        repo_url=repo_url,
        raw_payload=payload,
    )


def normalize_pr_event(payload: dict, delivery_id: str | None) -> PREvent | None:
    """Convert pull_request webhook payload to PREvent. Returns None if missing required fields."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    if not action or not pr or not repo:
        return None

    owner = repo.get("owner", {})
    if isinstance(owner, dict):
        owner_login = owner.get("login", "")
    else:
        owner_login = getattr(owner, "login", "") or ""

    repo_name = repo.get("name", "")
    full_name = repo.get("full_name", "")
    if not full_name and owner_login and repo_name:
        full_name = f"{owner_login}/{repo_name}"

    pr_number = pr.get("number", 0)
    head = pr.get("head", {})
    head_sha = head.get("sha", "")
    head_ref = head.get("ref", "")
    repo_url = repo.get("html_url", "") or (f"https://github.com/{full_name}" if full_name else "")
    installation_id = payload.get("installation", {}) or {}
    if isinstance(installation_id, dict):
        installation_id = installation_id.get("id", 0) or 0
    else:
        installation_id = getattr(installation_id, "id", 0) or 0

    labels_data = pr.get("labels", [])
    labels = [l.get("name", "") for l in labels_data] if isinstance(labels_data, list) else []
    user = pr.get("user", {})
    user_type = user.get("type", "") if isinstance(user, dict) else getattr(user, "type", "")

    settings = get_settings()
    trigger_label = settings.TRIGGER_LABEL
    is_agent_pr = (
        trigger_label in labels
        or user_type == "Bot"
        or (head_ref or "").startswith("agent/issue-")
    )

    return PREvent(
        action=str(action),
        delivery_id=delivery_id,
        sender=_sender_from_payload(payload),
        owner=owner_login,
        repo_name=repo_name,
        full_name=full_name,
        pr_number=pr_number,
        head_sha=head_sha,
        head_ref=head_ref,
        repo_url=repo_url,
        installation_id=int(installation_id) if installation_id else 0,
        labels=labels,
        is_agent_pr=is_agent_pr,
        raw_payload=payload,
    )


def normalize_workflow_run_event(
    payload: dict, delivery_id: str | None
) -> WorkflowRunEvent | None:
    """Convert workflow_run webhook payload to WorkflowRunEvent. Returns None if missing required fields."""
    action = payload.get("action")
    wr = payload.get("workflow_run", {})
    repo = payload.get("repository", {})
    if not action or not wr or not repo:
        return None

    full_name = repo.get("full_name", "")
    wr_id = wr.get("id") or wr.get("run_id") or ""
    workflow_name = wr.get("name", "")
    workflow = wr.get("workflow", {}) or {}
    workflow_path = wr.get("path") or workflow.get("path", "")
    head_sha = wr.get("head_sha", "")
    head_branch = wr.get("head_branch", "")
    conclusion = wr.get("conclusion")

    return WorkflowRunEvent(
        action=str(action),
        delivery_id=delivery_id,
        sender=_sender_from_payload(payload),
        full_name=full_name,
        workflow_run_id=wr_id,
        workflow_name=workflow_name,
        workflow_path=workflow_path,
        head_sha=head_sha,
        head_branch=head_branch,
        conclusion=conclusion,
        raw_payload=payload,
    )


def normalize(
    event_type: str,
    payload: dict,
    delivery_id: str | None,
) -> IssueEvent | PREvent | WorkflowRunEvent | None:
    """Dispatch by event_type. Returns None for unsupported types or invalid payloads."""
    if event_type == "issues":
        return normalize_issue_event(payload, delivery_id)
    if event_type == "pull_request":
        return normalize_pr_event(payload, delivery_id)
    if event_type == "workflow_run":
        return normalize_workflow_run_event(payload, delivery_id)
    return None
