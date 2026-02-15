"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI

from booty.code_gen.generator import process_issue_to_pr
from booty.config import get_settings, verifier_enabled
from booty.github.comments import post_failure_comment
from booty.jobs import Job, JobQueue
from booty.logging import configure_logging, get_logger
from booty.repositories import prepare_workspace
from booty.verifier import VerifierJob
from booty.verifier.queue import VerifierQueue
from booty.verifier.runner import process_verifier_job
from booty.webhooks import router as webhook_router


# Module-level job queue and app start time
job_queue: JobQueue | None = None
verifier_queue: VerifierQueue | None = None
app_start_time: datetime | None = None


def get_app_version() -> str:
    """Get the application version from package metadata.

    Returns:
        str: The version string, or "unknown" if version cannot be determined
    """
    try:
        return version("booty")
    except PackageNotFoundError:
        return "unknown"


async def process_job(job: Job) -> None:
    """Process a job by cloning repo and preparing workspace.

    Args:
        job: Job to process
    """
    logger = get_logger().bind(job_id=job.job_id, issue_number=job.issue_number)
    settings = get_settings()

    logger.info(
        "job_started",
        verifier_retries=job.verifier_retries,
        pr_number=job.pr_number,
    )

    # Use repo_url from the job if set (retries), otherwise from settings
    repo_url = job.repo_url or settings.TARGET_REPO_URL

    # Prepare workspace
    async with prepare_workspace(
        job, repo_url, settings.TARGET_BRANCH, settings.GITHUB_TOKEN
    ) as workspace:
        logger.info("workspace_ready", path=workspace.path, branch=workspace.branch)

        # Process issue through full pipeline
        pr_number, tests_passed, error_message = await process_issue_to_pr(
            job, workspace, settings, is_self_modification=job.is_self_modification
        )
        logger.info("pr_created", pr_number=pr_number, tests_passed=tests_passed)

        # If tests failed, post failure comment on issue
        # Skip for verifier retries — the push triggers re-verification automatically
        if not tests_passed and job.pr_number is None:
            logger.warning("tests_failed_posting_comment", pr_number=pr_number)
            post_failure_comment(
                settings.GITHUB_TOKEN,
                repo_url,
                job.issue_number,
                error_message or "Unknown error",
            )
            logger.info("job_completed_with_failures", pr_number=pr_number)
        elif not tests_passed:
            logger.info(
                "retry_completed_with_failures",
                pr_number=pr_number,
                verifier_retries=job.verifier_retries,
            )
        else:
            logger.info("job_completed_successfully", pr_number=pr_number)


async def _process_verifier_job(job: VerifierJob) -> None:
    """Wrapper to pass settings and job_queue to process_verifier_job."""
    settings = get_settings()
    await process_verifier_job(job, settings, job_queue=job_queue)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Configures logging, starts workers on startup, shuts down on exit.
    """
    global job_queue, verifier_queue, app_start_time

    settings = get_settings()
    logger = get_logger()

    # Startup
    configure_logging(settings.LOG_LEVEL)
    logger.info("app_starting", worker_count=settings.WORKER_COUNT)

    if not verifier_enabled(settings):
        logger.info(
            "verifier_disabled",
            reason="missing GITHUB_APP_ID or GITHUB_APP_PRIVATE_KEY",
        )

    # Record app start time
    app_start_time = datetime.now(timezone.utc)

    job_queue = JobQueue(maxsize=settings.QUEUE_MAX_SIZE)
    await job_queue.start_workers(settings.WORKER_COUNT, process_job)

    # Store job queue in app state for webhooks to access
    app.state.job_queue = job_queue

    # Verifier queue and workers
    if verifier_enabled(settings):
        verifier_queue = VerifierQueue(maxsize=100)
        await verifier_queue.start_workers(
            settings.VERIFIER_WORKER_COUNT,
            _process_verifier_job,
        )
        app.state.verifier_queue = verifier_queue
    else:
        verifier_queue = None
        app.state.verifier_queue = None

    logger.info("app_started")

    yield

    # Shutdown
    logger.info("app_shutting_down")
    if job_queue:
        await job_queue.shutdown()
    if verifier_queue:
        await verifier_queue.shutdown()
    logger.info("app_stopped")


app = FastAPI(
    title="Booty",
    description="Self-managing builder agent",
    lifespan=lifespan,
)

# Add correlation ID middleware FIRST
app.add_middleware(CorrelationIdMiddleware)

# Include routers
app.include_router(webhook_router)


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Status OK
    """
    return {"status": "ok"}


@app.get("/jobs")
async def list_jobs():
    """List recent job history.

    Returns:
        dict: JSON response with list of recent jobs including issue_number, status, and timestamp
    """
    if job_queue is None:
        return {"jobs": [], "error": "Job queue not initialized"}

    jobs = job_queue.get_recent_jobs(limit=100)
    return {"jobs": jobs, "total": len(jobs)}


@app.get("/info")
async def info():
    """Runtime diagnostics endpoint.

    Returns:
        dict: JSON response with app version, job statistics, worker count, and uptime
    """
    if job_queue is None or app_start_time is None:
        return {
            "error": "Application not fully initialized",
            "version": get_app_version(),
            "uptime_seconds": 0,
            "jobs": {
                "queued": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
            },
            "workers": {
                "active": 0,
            },
            "error": "Application not fully initialized",
        }

    # Calculate uptime
    current_time = datetime.now(timezone.utc)
    uptime_seconds = int((current_time - app_start_time).total_seconds())

    # Get job statistics
    job_stats = job_queue.get_job_stats()

    # Get active worker count
    active_workers = job_queue.get_active_worker_count()

    return {
        "version": get_app_version(),
        "uptime_seconds": uptime_seconds,
        "jobs": {
            "queued": job_stats["queued"],
            "running": job_stats["running"],
            "completed": job_stats["completed"],
            "failed": job_stats["failed"],
        },
        "workers": {
            "active": active_workers,
        },
    }
