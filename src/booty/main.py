"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI

from booty.config import get_settings
from booty.jobs import Job, JobQueue
from booty.logging import configure_logging, get_logger
from booty.repositories import prepare_workspace
from booty.webhooks import router as webhook_router


# Module-level job queue
job_queue: JobQueue | None = None


async def process_job(job: Job) -> None:
    """Process a job by cloning repo and preparing workspace.

    Args:
        job: Job to process
    """
    logger = get_logger().bind(job_id=job.job_id, issue_number=job.issue_number)
    settings = get_settings()

    logger.info("job_started")

    # Prepare workspace
    async with prepare_workspace(
        job, settings.TARGET_REPO_URL, settings.TARGET_BRANCH, settings.GITHUB_TOKEN
    ) as workspace:
        logger.info("workspace_ready", path=workspace.path, branch=workspace.branch)

        # Phase 2 will add LLM code generation here

        logger.info("job_completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Configures logging, starts workers on startup, shuts down on exit.
    """
    global job_queue

    settings = get_settings()
    logger = get_logger()

    # Startup
    configure_logging(settings.LOG_LEVEL)
    logger.info("app_starting", worker_count=settings.WORKER_COUNT)

    job_queue = JobQueue(maxsize=settings.QUEUE_MAX_SIZE)
    await job_queue.start_workers(settings.WORKER_COUNT, process_job)

    # Store job queue in app state for webhooks to access
    app.state.job_queue = job_queue

    logger.info("app_started")

    yield

    # Shutdown
    logger.info("app_shutting_down")
    if job_queue:
        await job_queue.shutdown()
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
