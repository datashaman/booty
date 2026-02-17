"""Canonical event router: normalize GitHub webhooks → internal events → enqueue."""

from booty.router.events import IssueEvent, PREvent, WorkflowRunEvent
from booty.router.normalizer import (
    normalize,
    normalize_issue_event,
    normalize_pr_event,
    normalize_workflow_run_event,
)

__all__ = [
    "IssueEvent",
    "PREvent",
    "WorkflowRunEvent",
    "normalize",
    "normalize_issue_event",
    "normalize_pr_event",
    "normalize_workflow_run_event",
]
