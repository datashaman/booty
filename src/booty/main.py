"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

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

    try:
        # Use repo_url from the job if set (retries), otherwise from settings
        repo_url = job.repo_url or settings.TARGET_REPO_URL

        # Prepare workspace
        async with prepare_workspace(
            job, repo_url, settings.TARGET_BRANCH, settings.GITHUB_TOKEN
        ) as workspace:
            logger.info("workspace_ready", path=workspace.path, branch=workspace.branch)

            try:
                # Process issue through full pipeline
                pr_number, tests_passed, error_message = await process_issue_to_pr(
                    job, workspace, settings, is_self_modification=job.is_self_modification
                )
            except Exception as e:
                # Pipeline crashed before PR was created — post on issue as fallback
                logger.error(
                    "pipeline_exception",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                try:
                    post_failure_comment(
                        settings.GITHUB_TOKEN,
                        repo_url,
                        job.issue_number,
                        str(e),
                    )
                except Exception as comment_error:
                    logger.error(
                        "failed_to_post_failure_comment",
                        error=str(comment_error),
                        error_type=type(comment_error).__name__,
                        exc_info=True,
                    )
                return

            logger.info("pr_created", pr_number=pr_number, tests_passed=tests_passed)

            # Test failure feedback goes on the PR via the Verifier, not the issue
            if not tests_passed:
                logger.info(
                    "job_completed_with_failures",
                    pr_number=pr_number,
                    verifier_retries=job.verifier_retries,
                )
            else:
                logger.info("job_completed_successfully", pr_number=pr_number)

    except Exception as e:
        # Catch any unexpected errors in job processing
        logger.error(
            "job_processing_error",
            error=str(e),
            error_type=type(e).__name__,
            job_id=job.job_id,
            issue_number=job.issue_number,
            exc_info=True,
        )
        raise


async def _process_verifier_job(job: VerifierJob) -> None:
    """Wrapper to pass settings and job_queue to process_verifier_job."""
    logger = get_logger().bind(
        verifier_job_id=job.job_id,
        pr_number=job.pr_number,
    )
    try:
        settings = get_settings()
        await process_verifier_job(job, settings, job_queue=job_queue)
    except Exception as e:
        logger.error(
            "verifier_job_processing_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Configures logging, starts workers on startup, shuts down on exit.
    """
    global job_queue, verifier_queue, app_start_time

    settings = get_settings()
    logger = get_logger()

    try:
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

        try:
            job_queue = JobQueue(maxsize=settings.QUEUE_MAX_SIZE)
            await job_queue.start_workers(settings.WORKER_COUNT, process_job)
            logger.info("job_queue_started", worker_count=settings.WORKER_COUNT)
        except Exception as e:
            logger.error(
                "job_queue_startup_error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

        # Store job queue in app state for webhooks to access
        app.state.job_queue = job_queue

        # Verifier queue and workers
        if verifier_enabled(settings):
            try:
                verifier_queue = VerifierQueue(maxsize=100)
                await verifier_queue.start_workers(
                    settings.VERIFIER_WORKER_COUNT,
                    _process_verifier_job,
                )
                app.state.verifier_queue = verifier_queue
                logger.info(
                    "verifier_queue_started",
                    worker_count=settings.VERIFIER_WORKER_COUNT,
                )
            except Exception as e:
                logger.error(
                    "verifier_queue_startup_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                raise
        else:
            verifier_queue = None
            app.state.verifier_queue = None

        logger.info("app_started")

        yield

    except Exception as e:
        logger.error(
            "app_startup_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise
    finally:
        # Shutdown
        logger.info("app_shutting_down")
        try:
            if job_queue:
                await job_queue.shutdown()
                logger.info("job_queue_shutdown_complete")
        except Exception as e:
            logger.error(
                "job_queue_shutdown_error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )

        try:
            if verifier_queue:
                await verifier_queue.shutdown()
                logger.info("verifier_queue_shutdown_complete")
        except Exception as e:
            logger.error(
                "verifier_queue_shutdown_error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )

        logger.info("app_stopped")


app = FastAPI(
    title="Booty",
    description="Self-managing builder agent",
    lifespan=lifespan,
)

# Add correlation ID middleware FIRST
app.add_middleware(CorrelationIdMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to catch and log all unhandled exceptions.

    Args:
        request: The incoming request
        exc: The exception that was raised

    Returns:
        JSONResponse with error details
    """
    logger = get_logger()
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "type": type(exc).__name__,
            "message": str(exc),
        },
    )


# Include routers
app.include_router(webhook_router)


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Status OK
    """
    logger = get_logger()
    try:
        return {"status": "ok"}
    except Exception as e:
        logger.error(
            "health_check_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise


@app.get("/jobs")
async def list_jobs():
    """List recent job history.

    Returns:
        dict: JSON response with list of recent jobs including issue_number, status, and timestamp
    """
    logger = get_logger()
    try:
        if job_queue is None:
            logger.warning("list_jobs_called_before_initialization")
            return {"jobs": [], "error": "Job queue not initialized"}

        jobs = job_queue.get_recent_jobs(limit=100)
        return {"jobs": jobs, "total": len(jobs)}
    except Exception as e:
        logger.error(
            "list_jobs_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise


@app.get("/info")
async def info():
    """Runtime diagnostics endpoint.

    Returns:
        dict: JSON response with app version, job statistics, worker count, and uptime
    """
    logger = get_logger()
    try:
        if job_queue is None or app_start_time is None:
            logger.warning("info_called_before_initialization")
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
    except Exception as e:
        logger.error(
            "info_endpoint_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise
