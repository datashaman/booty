"""Security job runner — check lifecycle and config loading."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from github import UnknownObjectException

from booty.config import Settings, security_enabled
from booty.github.checks import (
    create_security_check_run,
    edit_check_run,
    get_verifier_repo,
)
from booty.logging import get_logger
from booty.security.audit import AuditResult, run_dependency_audit
from booty.security.job import SecurityJob
from booty.security.override import persist_override
from booty.security.permission_drift import (
    _title_for_paths,
    get_changed_paths,
    sensitive_paths_touched,
)
from booty.security.scanner import build_annotations, run_secret_scan
from booty.test_runner.config import (
    BootyConfigV1,
    SecurityConfig,
    apply_security_env_overrides,
    load_booty_config_from_content,
)
from booty.verifier.workspace import prepare_verification_workspace

if TYPE_CHECKING:
    pass

logger = get_logger()


def build_audit_summary(audit_result: AuditResult) -> str:
    """Build summary text for dependency audit results.

    Group by ecosystem; failed ecosystems first. Cap findings at 100.
    """
    lines: list[str] = []

    # Group findings by ecosystem
    by_eco: dict[str, list[dict]] = {}
    for f in audit_result.findings[:100]:
        eco = f.get("ecosystem", "unknown")
        by_eco.setdefault(eco, []).append(f)

    # Failed ecosystems first (have high/critical findings)
    for eco, findings in sorted(by_eco.items()):
        high = sum(1 for x in findings if x.get("severity") == "high")
        critical = sum(1 for x in findings if x.get("severity") == "critical")
        paths = sorted({str(f.get("path", "")) for f in findings if f.get("path")})
        path_str = ", ".join(paths[:5])
        if len(paths) > 5:
            path_str += f", ... ({len(paths)} total)"
        lines.append(f"{eco}: {critical} critical, {high} high. Affected: {path_str}")

    if audit_result.errors:
        lines.append("Errors: " + "; ".join(audit_result.errors[:3]))
        if len(audit_result.errors) > 3:
            lines[-1] += f" ({len(audit_result.errors)} total)"

    return "\n".join(lines) if lines else "Dependency audit failed"


async def process_security_job(job: SecurityJob, settings: Settings) -> None:
    """Process a security job: create check, load config, complete.

    Check run lifecycle: queued → in_progress → completed (success).
    Phase 18 baseline: no actual scanning; load config and complete success.
    """
    if not security_enabled(settings):
        logger.info(
            "security_skipped",
            job_id=job.job_id,
            reason="security_disabled",
        )
        return

    check_run = create_security_check_run(
        job.owner,
        job.repo_name,
        job.head_sha,
        job.installation_id,
        settings,
        status="queued",
    )
    if check_run is None:
        logger.info(
            "security_skipped",
            job_id=job.job_id,
            reason="check_run_failed",
        )
        return

    logger.info("security_check_created", job_id=job.job_id, status="queued")

    edit_check_run(
        check_run,
        status="in_progress",
        output={
            "title": "Booty Security",
            "summary": "Scanning for secrets and vulnerabilities…",
        },
    )
    logger.info("security_check_in_progress", job_id=job.job_id)

    # Load config from repo
    security_config = None
    repo = get_verifier_repo(
        job.owner,
        job.repo_name,
        job.installation_id,
        settings,
    )
    if repo is not None:
        try:
            fc = repo.get_contents(".booty.yml", ref=job.head_sha)
            content = fc.decoded_content.decode()
            config = load_booty_config_from_content(content)
            if isinstance(config, BootyConfigV1) and config.security is not None:
                security_config = apply_security_env_overrides(config.security)
        except UnknownObjectException:
            # No .booty.yml — treat as Security enabled (default)
            security_config = None
        except Exception as e:
            logger.warning(
                "security_config_load_failed",
                job_id=job.job_id,
                error=str(e),
            )

    # Phase 18: if security disabled in config, complete success
    if security_config is not None and not security_config.enabled:
        edit_check_run(
            check_run,
            status="completed",
            conclusion="success",
            output={
                "title": "Security check complete",
                "summary": "Security check complete — disabled",
            },
        )
        logger.info("security_check_completed", job_id=job.job_id, conclusion="success")
        return

    # Phase 19: run secret scan
    base_sha = job.base_sha or (job.payload.get("pull_request", {}).get("base", {}).get("sha", ""))
    try:
        async with prepare_verification_workspace(
            job.repo_url,
            job.head_sha,
            settings.GITHUB_TOKEN,
            job.head_ref,
        ) as workspace:
            # If base_sha is None/empty, use head_sha as base to produce empty diff
            # (no changed files to scan). This gracefully handles initial commits.
            scan_base = base_sha if base_sha else job.head_sha
            result = await asyncio.to_thread(
                run_secret_scan,
                workspace.path,
                scan_base,
                security_config,
            )

            if not result.scan_ok:
                edit_check_run(
                    check_run,
                    status="completed",
                    conclusion="failure",
                    output={
                        "title": "Security failed — secret detected",
                        "summary": result.error_message or "Scan incomplete",
                    },
                )
                logger.info("security_check_completed", job_id=job.job_id, conclusion="failure")
                return

            if result.findings:
                annotations, suffix = build_annotations(result.findings, 50)
                num_files = len({f.get("path", "") for f in result.findings})
                summary = f"{len(result.findings)} secret(s) in {num_files} file(s){suffix}"
                edit_check_run(
                    check_run,
                    status="completed",
                    conclusion="failure",
                    output={
                        "title": "Security failed — secret detected",
                        "summary": summary,
                        "annotations": annotations,
                    },
                )
                logger.info("security_check_completed", job_id=job.job_id, conclusion="failure")
                return

            # Phase 20: run dependency audit after secret scan
            try:
                audit_result = await asyncio.to_thread(
                    run_dependency_audit,
                    workspace.path,
                    security_config,
                )
            except Exception as e:
                logger.exception("dependency_audit_failed", job_id=job.job_id, error=str(e))
                edit_check_run(
                    check_run,
                    status="completed",
                    conclusion="failure",
                    output={
                        "title": "Security failed — high vulnerability",
                        "summary": f"Audit timed out or failed: {e!s}",
                    },
                )
                logger.info("security_check_completed", job_id=job.job_id, conclusion="failure")
                return

            if not audit_result.ok:
                title = (
                    "Security failed — critical vulnerability"
                    if audit_result.worst_severity == "critical"
                    else "Security failed — high vulnerability"
                )
                summary = build_audit_summary(audit_result)
                edit_check_run(
                    check_run,
                    status="completed",
                    conclusion="failure",
                    output={"title": title, "summary": summary},
                )
                logger.info("security_check_completed", job_id=job.job_id, conclusion="failure")
                return

            # Both secret scan and dependency audit passed — check permission drift
            sensitive_paths = (
                security_config.sensitive_paths
                if security_config
                else SecurityConfig().sensitive_paths
            )
            paths = get_changed_paths(
                workspace.repo,
                base_sha or job.head_sha,
                job.head_sha,
            )
            touched = sensitive_paths_touched(paths, sensitive_paths)
            if touched:
                title = _title_for_paths(touched)
                summary = (
                    "Paths that triggered escalation: "
                    + ", ".join(sorted(touched)[:10])
                    + (" …" if len(touched) > 10 else "")
                )
                edit_check_run(
                    check_run,
                    status="completed",
                    conclusion="success",
                    output={"title": title, "summary": summary},
                )
                repo_full_name = f"{job.owner}/{job.repo_name}"
                persist_override(repo_full_name, job.head_sha, touched)
                logger.info(
                    "security_escalated",
                    job_id=job.job_id,
                    paths=touched,
                )
                return

            # No sensitive paths touched — final success
            eco_count = len(
                {k.split(":")[0] for k in audit_result.summary_by_ecosystem}
            )
            summary = "No secrets detected."
            if eco_count > 0:
                summary += f" All dependency audits passed ({eco_count} ecosystem(s))."
            else:
                summary += " No dependency lockfiles found."

            edit_check_run(
                check_run,
                status="completed",
                conclusion="success",
                output={
                    "title": "Security check complete",
                    "summary": summary,
                },
            )
            logger.info("security_check_completed", job_id=job.job_id, conclusion="success")

    except Exception as e:
        logger.exception("security_scan_failed", job_id=job.job_id, error=str(e))
        edit_check_run(
            check_run,
            status="completed",
            conclusion="failure",
            output={
                "title": "Security check failed",
                "summary": f"Scan incomplete: {e!s}",
            },
        )
        logger.info("security_check_completed", job_id=job.job_id, conclusion="failure")
