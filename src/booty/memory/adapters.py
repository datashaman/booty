"""Memory adapter functions — build record dicts for each ingestion source."""

import hashlib
from datetime import datetime, timezone

from booty.github.issues import build_sentry_issue_title


def build_incident_record(event: dict, issue_number: int, repo: str) -> dict:
    """Build incident record from Sentry event and issue number."""
    severity = event.get("level", "error")
    fingerprint = (
        event.get("fingerprint")
        or event.get("issue_id", "")
        or (event.get("culprit", "")[:200] if event.get("culprit") else "")
    )
    title = build_sentry_issue_title(event)
    timestamp = event.get("datetime") or event.get("timestamp") or datetime.now(timezone.utc).isoformat()
    return {
        "type": "incident",
        "repo": repo,
        "source": "observability",
        "severity": severity,
        "fingerprint": fingerprint or "",
        "title": title,
        "summary": f"Sentry issue #{issue_number}",
        "sha": "",
        "pr_number": None,
        "links": [{"url": f"https://github.com/{repo}/issues/{issue_number}", "type": "github_issue"}],
        "metadata": {
            "issue_id": event.get("issue_id", ""),
            "sentry_event": event.get("id"),
        },
        "timestamp": timestamp,
    }


def build_governor_hold_record(decision, repo: str) -> dict:
    """Build governor_hold record from Governor decision."""
    sha = getattr(decision, "sha", "")
    sha_short = sha[:7] if sha else "?"
    severity = "high" if getattr(decision, "risk_class", "") == "HIGH" else "medium"
    return {
        "type": "governor_hold",
        "repo": repo,
        "sha": sha,
        "source": "governor",
        "fingerprint": getattr(decision, "reason", ""),
        "severity": severity,
        "title": f"HOLD: {getattr(decision, 'reason', '')} — {sha_short}",
        "summary": f"Governor held deploy: {getattr(decision, 'reason', '')}",
        "pr_number": None,
        "metadata": {
            "reason": getattr(decision, "reason", ""),
            "risk_class": getattr(decision, "risk_class", ""),
        },
    }


def build_deploy_failure_record(
    sha: str, run_url: str, conclusion: str, failure_type: str, repo: str
) -> dict:
    """Build deploy_failure record."""
    sha_short = sha[:7] if sha else "?"
    return {
        "type": "deploy_failure",
        "repo": repo,
        "sha": sha,
        "source": "governor",
        "fingerprint": sha,
        "severity": "high",
        "title": f"Deploy failure: {sha_short}",
        "summary": f"Deploy {conclusion} — {failure_type}",
        "links": [{"url": run_url, "type": "workflow_run"}],
        "metadata": {"conclusion": conclusion, "failure_type": failure_type},
    }


def build_security_block_record(
    job, trigger: str, title: str, summary: str, paths: list[str]
) -> dict:
    """Build security_block record from SecurityJob."""
    repo = f"{job.owner}/{job.repo_name}"
    sha = job.head_sha
    sha_short = sha[:7] if sha else "?"
    fingerprint = f"security:{trigger}:{sha_short}"
    severity = "high" if trigger in ("secret", "vulnerability") else "medium"
    return {
        "type": "security_block",
        "repo": repo,
        "sha": sha,
        "pr_number": job.pr_number,
        "source": "security",
        "fingerprint": fingerprint,
        "severity": severity,
        "title": title,
        "summary": summary,
        "paths": paths or [],
        "metadata": {"trigger": trigger},
    }


def build_verifier_cluster_record(
    job, failure_type: str, paths: list[str], summary: str
) -> dict:
    """Build verifier_cluster record from VerifierJob."""
    repo = f"{job.owner}/{job.repo_name}"
    if paths:
        path_key = hashlib.sha256("|".join(sorted(paths)).encode()).hexdigest()[:16]
        fingerprint = f"{failure_type}:{path_key}"
    else:
        fingerprint = f"{failure_type}:{job.head_sha[:7] if job.head_sha else '?'}"
    return {
        "type": "verifier_cluster",
        "repo": repo,
        "sha": job.head_sha,
        "pr_number": job.pr_number,
        "source": "verifier",
        "fingerprint": fingerprint,
        "severity": "high",
        "title": summary[:200] if summary else f"Verifier {failure_type} failed",
        "summary": summary,
        "paths": paths or [],
        "metadata": {"failure_type": failure_type},
    }


def build_revert_record(repo: str, sha: str, reverted_sha: str, source: str = "push") -> dict:
    """Build revert record."""
    reverted_short = reverted_sha[:7] if reverted_sha else "?"
    return {
        "type": "revert",
        "repo": repo,
        "sha": sha,
        "source": source,
        "fingerprint": sha,
        "title": f"Revert {reverted_short}",
        "summary": f"Reverted commit {reverted_short}",
        "metadata": {"reverted_sha": reverted_sha},
    }
