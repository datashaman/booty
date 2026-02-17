"""Internal event structs for routing GitHub webhook events.

Typed event families carry routing fields and raw_payload for agent-specific parsing.
ROUTE-01: extracted normalization layer before enqueue.
"""

from dataclasses import dataclass


@dataclass
class IssueEvent:
    """Normalized issue event for planner/builder routing."""

    action: str
    delivery_id: str | None
    sender: str | None
    owner: str
    repo_name: str
    full_name: str
    issue_number: int
    labels: list[str]
    repo_url: str
    raw_payload: dict


@dataclass
class PREvent:
    """Normalized pull_request event for reviewer/verifier/security routing."""

    action: str
    delivery_id: str | None
    sender: str | None
    owner: str
    repo_name: str
    full_name: str
    pr_number: int
    head_sha: str
    head_ref: str
    repo_url: str
    installation_id: int
    labels: list[str]
    is_agent_pr: bool
    raw_payload: dict


@dataclass
class WorkflowRunEvent:
    """Normalized workflow_run event for governor.evaluate/observe_deploy."""

    action: str
    delivery_id: str | None
    sender: str | None
    full_name: str
    workflow_run_id: int | str
    workflow_name: str
    workflow_path: str
    head_sha: str
    head_branch: str
    conclusion: str | None
    raw_payload: dict
