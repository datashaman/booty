"""Security job definition."""

from dataclasses import dataclass


@dataclass
class SecurityJob:
    """Security scan job for a pull request."""

    job_id: str
    owner: str
    repo_name: str
    pr_number: int
    head_sha: str
    head_ref: str
    base_sha: str
    repo_url: str
    installation_id: int
    payload: dict
