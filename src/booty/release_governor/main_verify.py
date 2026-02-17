"""Main-branch verification for Release Governor — Booty-owned alternative to verify-main workflow."""

from __future__ import annotations

import asyncio
import subprocess
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from github import Auth, Github

from booty.config import get_settings
from booty.github.repo_config import load_booty_config_for_repo
from booty.logging import get_logger
from booty.release_governor.decision import Decision
from booty.release_governor.handler import apply_governor_decision, simulate_decision_for_cli
from booty.release_governor.store import get_state_dir, has_delivery_id, record_delivery_id
from booty.release_governor.ux import post_hold_status
from booty.test_runner.config import (
    apply_release_governor_env_overrides,
    load_booty_config,
)
from booty.test_runner.executor import execute_tests
from booty.verifier.workspace import prepare_verification_workspace

logger = get_logger()


@dataclass
class MainVerificationJob:
    """Verification job for main branch — triggers Governor on success."""

    repo_full_name: str
    head_sha: str
    repo_url: str
    delivery_id: str


def _dedup_key(repo_full_name: str, head_sha: str) -> str:
    return f"{repo_full_name}:main:{head_sha}"


class MainVerificationQueue:
    """Async queue for MainVerificationJobs with (repo, head_sha) deduplication."""

    def __init__(self, maxsize: int = 50):
        self._queue: asyncio.Queue[MainVerificationJob] = asyncio.Queue(maxsize=maxsize)
        self._processed: set[str] = set()
        self._processed_order: deque[str] = deque()
        self._worker_tasks: list[asyncio.Task] = []
        self._logger = get_logger()

    def is_duplicate(self, repo_full_name: str, head_sha: str) -> bool:
        """Check if this repo+head_sha was already processed or enqueued."""
        return _dedup_key(repo_full_name, head_sha) in self._processed

    def _mark_processed(self, repo_full_name: str, head_sha: str) -> None:
        key = _dedup_key(repo_full_name, head_sha)
        self._processed.add(key)
        self._processed_order.append(key)
        if len(self._processed) > 5000:
            oldest = self._processed_order.popleft()
            self._processed.discard(oldest)

    async def enqueue(self, job: MainVerificationJob) -> bool:
        """Enqueue a main verification job. Returns False if duplicate."""
        key = _dedup_key(job.repo_full_name, job.head_sha)
        if key in self._processed:
            self._logger.warning(
                "main_verify_duplicate",
                repo=job.repo_full_name,
                head_sha=job.head_sha[:7],
            )
            return False

        self._mark_processed(job.repo_full_name, job.head_sha)

        try:
            await asyncio.wait_for(self._queue.put(job), timeout=5.0)
            self._logger.info(
                "main_verify_enqueued",
                repo=job.repo_full_name,
                head_sha=job.head_sha[:7],
                queue_size=self._queue.qsize(),
            )
            return True
        except asyncio.TimeoutError:
            self._logger.error(
                "main_verify_enqueue_timeout",
                repo=job.repo_full_name,
                head_sha=job.head_sha[:7],
            )
            self._processed.discard(key)
            return False

    async def worker(
        self,
        worker_id: int,
        process_fn: Callable[[MainVerificationJob], Awaitable[None]],
    ) -> None:
        """Worker loop that processes MainVerificationJobs."""
        log = self._logger.bind(worker_id=worker_id)
        log.info("main_verify_worker_started")

        while True:
            try:
                job = await self._queue.get()
                log = log.bind(repo=job.repo_full_name, head_sha=job.head_sha[:7])
                log.info("main_verify_job_started")

                try:
                    await process_fn(job)
                    log.info("main_verify_job_completed")
                except Exception as e:
                    log.error(
                        "main_verify_job_failed",
                        error=str(e),
                        exc_info=True,
                    )
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                log.info("main_verify_worker_cancelled")
                break
            except Exception as e:
                log.error("main_verify_worker_error", error=str(e), exc_info=True)

    async def start_workers(
        self,
        num_workers: int,
        process_fn: Callable[[MainVerificationJob], Awaitable[None]],
    ) -> None:
        """Start main verification worker tasks."""
        self._logger.info("main_verify_workers_starting", num_workers=num_workers)
        for i in range(num_workers):
            task = asyncio.create_task(self.worker(i, process_fn))
            self._worker_tasks.append(task)

    async def shutdown(self) -> None:
        """Gracefully shutdown main verification workers."""
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()


def _apply_verification_failed(
    repo_full_name: str,
    head_sha: str,
    hold_docs_url: str,
) -> None:
    """Post HOLD status with verification_failed reason."""
    settings = get_settings()
    decision = Decision("HOLD", "verification_failed", "HIGH", head_sha)
    gh = Github(auth=Auth.Token(settings.GITHUB_TOKEN))
    gh_repo = gh.get_repo(repo_full_name)
    post_hold_status(gh_repo, head_sha, decision, hold_docs_url)


async def process_main_verification_job(job: MainVerificationJob) -> None:
    """Run verification on main at head_sha, then Governor evaluates on success."""
    settings = get_settings()
    state_dir = get_state_dir()
    html_url = f"https://github.com/{job.repo_full_name}"
    default_branch = "main"
    hold_docs_url = f"{html_url}/blob/{default_branch}/docs/release-governor.md"
    actions_url = f"{html_url}/actions"

    if has_delivery_id(state_dir, job.repo_full_name, job.head_sha):
        logger.info(
            "main_verify_skipped",
            repo=job.repo_full_name,
            head_sha=job.head_sha[:7],
            reason="already_processed",
        )
        return

    booty_config = load_booty_config_for_repo(job.repo_url, settings.GITHUB_TOKEN)
    if not booty_config or not getattr(booty_config, "release_governor", None):
        logger.info("main_verify_skipped", repo=job.repo_full_name, reason="no_governor_config")
        return

    gov_config = apply_release_governor_env_overrides(booty_config.release_governor)
    if not gov_config.enabled or not gov_config.deploy_workflow_name:
        logger.info("main_verify_skipped", repo=job.repo_full_name, reason="governor_disabled")
        return

    github_token = settings.GITHUB_TOKEN or ""
    verification_passed = False
    config_from_workspace = None

    try:
        async with prepare_verification_workspace(
            job.repo_url,
            job.head_sha,
            github_token=github_token,
            head_ref="main",
            base_ref="main",
        ) as workspace:
            ws_path = Path(workspace.path)
            config_from_workspace = load_booty_config(ws_path)

            setup = getattr(config_from_workspace, "setup_command", None)
            install = getattr(config_from_workspace, "install_command", None)
            if setup:
                r = subprocess.run(
                    setup, shell=True, cwd=ws_path, capture_output=True, text=True, timeout=300
                )
                if r.returncode != 0:
                    _apply_verification_failed(job.repo_full_name, job.head_sha, hold_docs_url)
                    record_delivery_id(state_dir, job.repo_full_name, job.head_sha, job.delivery_id)
                    return
            if install:
                r = subprocess.run(
                    install, shell=True, cwd=ws_path, capture_output=True, text=True, timeout=600
                )
                if r.returncode != 0:
                    _apply_verification_failed(job.repo_full_name, job.head_sha, hold_docs_url)
                    record_delivery_id(state_dir, job.repo_full_name, job.head_sha, job.delivery_id)
                    return

            timeout_sec = (
                getattr(config_from_workspace, "timeout_seconds", None)
                or getattr(config_from_workspace, "timeout", 600)
            )
            result = await execute_tests(
                config_from_workspace.test_command, timeout_sec, ws_path
            )

            if result.exit_code != 0:
                _apply_verification_failed(job.repo_full_name, job.head_sha, hold_docs_url)
                record_delivery_id(state_dir, job.repo_full_name, job.head_sha, job.delivery_id)
                return

            verification_passed = True

    except Exception as e:
        logger.exception("main_verify_workspace_error", repo=job.repo_full_name, error=str(e))
        _apply_verification_failed(job.repo_full_name, job.head_sha, hold_docs_url)
        record_delivery_id(state_dir, job.repo_full_name, job.head_sha, job.delivery_id)
        return

    if not verification_passed or not config_from_workspace:
        return

    rg = getattr(config_from_workspace, "release_governor", None)
    if not rg:
        logger.info("main_verify_skipped", repo=job.repo_full_name, reason="no_release_governor_in_workspace")
        return

    gov_config = apply_release_governor_env_overrides(rg)
    decision, _ = simulate_decision_for_cli(
        job.repo_full_name,
        job.head_sha,
        gov_config,
        Path("."),
        state_dir_override=state_dir,
    )

    gh = Github(auth=Auth.Token(settings.GITHUB_TOKEN))
    gh_repo = gh.get_repo(job.repo_full_name)

    apply_governor_decision(
        gh_repo,
        job.head_sha,
        decision,
        gov_config,
        job.repo_full_name,
        html_url,
        job.delivery_id,
        state_dir,
        booty_config=config_from_workspace,
    )

    logger.info(
        "main_verify_governor_processed",
        repo=job.repo_full_name,
        head_sha=job.head_sha[:7],
        outcome=decision.outcome,
        reason=decision.reason,
    )
