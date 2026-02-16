"""FastAPI application entrypoint."""

# Load .env into os.environ so RELEASE_GOVERNOR_*, SECURITY_*, etc. are available
# to code that uses os.environ.get() (pydantic-settings only reads .env for Settings).
from dotenv import load_dotenv

load_dotenv()

import asyncio
import sys
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from importlib.metadata import version, PackageNotFoundError

import sentry_sdk
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Header, HTTPException, Request
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from booty.code_gen.generator import process_issue_to_pr
from booty.config import get_settings, security_enabled, verifier_enabled
from booty.github.comments import post_failure_comment
from booty.jobs import Job, JobQueue
from booty.logging import configure_logging, get_logger
from booty.repositories import prepare_workspace
from booty.security import SecurityJob, SecurityQueue
from booty.security.runner import process_security_job
from booty.verifier import VerifierJob
from booty.verifier.queue import VerifierQueue
from booty.verifier.runner import process_verifier_job
from booty.webhooks import router as webhook_router
from booty.planner.jobs import planner_queue
from booty.planner.worker import process_planner_job


# Module-level job queue and app start time
job_queue: JobQueue | None = None
verifier_queue: VerifierQueue | None = None
security_queue: SecurityQueue | None = None
app_start_time: datetime | None = None


class SimpleRateLimiter:
    """Simple in-memory rate limiter for internal endpoints.
    
    Tracks request counts per IP address within a sliding time window.
    Automatically cleans up old entries to prevent memory growth.
    """
    
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        """Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[datetime]] = defaultdict(list)
    
    def is_rate_limited(self, identifier: str) -> bool:
        """Check if identifier is rate limited.
        
        Args:
            identifier: Unique identifier (e.g., IP address)
            
        Returns:
            True if rate limited, False otherwise
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > cutoff
        ]
        
        # Check if over limit
        if len(self.requests[identifier]) >= self.max_requests:
            return True
        
        # Record this request
        self.requests[identifier].append(now)
        return False
    
    def cleanup_old_entries(self) -> None:
        """Remove identifiers with no recent requests to prevent memory growth.
        
        Uses a cutoff of 2x the rate limit window to ensure entries aren't
        prematurely removed while still potentially relevant for rate limiting.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds * 2)
        
        identifiers_to_remove = [
            identifier for identifier, requests in self.requests.items()
            if not requests or all(req_time < cutoff for req_time in requests)
        ]
        
        for identifier in identifiers_to_remove:
            del self.requests[identifier]


# Rate limiter for internal test endpoints
internal_endpoint_limiter = SimpleRateLimiter(max_requests=5, window_seconds=60)


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

        try:
            # Process issue through full pipeline
            pr_number, tests_passed, error_message = await process_issue_to_pr(
                job, workspace, settings, is_self_modification=job.is_self_modification
            )
        except Exception as e:
            # Pipeline crashed before PR was created — post on issue as fallback
            logger.error("pipeline_exception", error=str(e), exc_info=True)
            sentry_sdk.set_tag("job_id", job.job_id)
            sentry_sdk.set_tag("issue_number", str(job.issue_number))
            sentry_sdk.capture_exception(e)
            post_failure_comment(
                settings.GITHUB_TOKEN,
                repo_url,
                job.issue_number,
                str(e),
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


def _init_sentry(settings) -> None:
    """Initialize Sentry SDK. Production without DSN fails startup."""
    env = (settings.SENTRY_ENVIRONMENT or "development").lower()
    is_production = env in ("production", "prod")
    dsn = (settings.SENTRY_DSN or "").strip()

    if not dsn:
        if is_production:
            get_logger().error(
                "sentry_disabled",
                msg="Sentry disabled — production requires DSN; refusing to start",
            )
            sys.exit(1)
        get_logger().info(
            "sentry_disabled",
            msg="Sentry disabled — no DSN configured",
            environment=env or "development",
        )
        return

    release = settings.SENTRY_RELEASE.strip() or None  # Never empty string
    sentry_sdk.init(
        dsn=dsn,
        release=release,
        environment=settings.SENTRY_ENVIRONMENT,
        sample_rate=settings.SENTRY_SAMPLE_RATE,
        traces_sample_rate=0,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )


async def _process_verifier_job(job: VerifierJob) -> None:
    """Wrapper to pass settings and job_queue to process_verifier_job."""
    settings = get_settings()
    try:
        await process_verifier_job(job, settings, job_queue=job_queue)
    except Exception as e:
        sentry_sdk.set_tag("job_id", job.job_id)
        sentry_sdk.capture_exception(e)
        logger = get_logger().bind(job_id=job.job_id, pr_number=job.pr_number)
        logger.error("verifier_job_exception", error=str(e), exc_info=True)
        raise


async def _process_security_job(job: SecurityJob) -> None:
    """Wrapper to pass settings to process_security_job."""
    settings = get_settings()
    try:
        await process_security_job(job, settings)
    except Exception as e:
        sentry_sdk.set_tag("job_id", job.job_id)
        sentry_sdk.capture_exception(e)
        logger = get_logger().bind(job_id=job.job_id, pr_number=job.pr_number)
        logger.error("security_job_exception", error=str(e), exc_info=True)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Configures logging, starts workers on startup, shuts down on exit.
    """
    global job_queue, verifier_queue, security_queue, app_start_time

    settings = get_settings()
    logger = get_logger()

    # Startup
    configure_logging(settings.LOG_LEVEL)
    logger.info("app_starting", worker_count=settings.WORKER_COUNT)

    # Sentry init (before job queue — must run before any traffic)
    _init_sentry(settings)

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

    # Security queue and workers
    if security_enabled(settings):
        security_queue = SecurityQueue(maxsize=100)
        await security_queue.start_workers(
            settings.SECURITY_WORKER_COUNT,
            _process_security_job,
        )
        app.state.security_queue = security_queue
    else:
        security_queue = None
        app.state.security_queue = None

    # Planner worker (single worker for Phase 27)
    async def _planner_worker_loop() -> None:
        while True:
            try:
                job = await planner_queue.get()
                try:
                    await asyncio.to_thread(process_planner_job, job)
                except Exception as e:
                    get_logger().error(
                        "planner_job_failed",
                        job_id=job.job_id,
                        error=str(e),
                        exc_info=True,
                    )
                finally:
                    planner_queue.task_done()
            except asyncio.CancelledError:
                break

    planner_worker_task = asyncio.create_task(_planner_worker_loop())
    app.state.planner_worker_task = planner_worker_task

    logger.info("app_started")

    yield

    # Shutdown
    logger.info("app_shutting_down")
    if job_queue:
        await job_queue.shutdown()
    if verifier_queue:
        await verifier_queue.shutdown()
    if security_queue:
        await security_queue.shutdown()
    planner_worker_task = getattr(app.state, "planner_worker_task", None)
    if planner_worker_task:
        planner_worker_task.cancel()
        try:
            await planner_worker_task
        except asyncio.CancelledError:
            pass
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


@app.get("/internal/sentry-test")
async def sentry_test(request: Request, x_internal_token: str = Header(None)):
    """Raise test exception for manual E2E Sentry verification. Hit with SENTRY_DSN set.
    
    Authentication:
    - In production (SENTRY_ENVIRONMENT=production): Requires X-Internal-Token header
    - When INTERNAL_TEST_TOKEN is set: Requires matching X-Internal-Token header
    - In development (no token configured): No authentication required
    
    Rate limiting: 5 requests per 60 seconds per IP to prevent Sentry quota exhaustion.
    """
    settings = get_settings()
    
    # Apply rate limiting based on client IP
    # Reject requests without valid client IP to prevent shared rate limit bucket
    if not request.client or not request.client.host:
        raise HTTPException(
            status_code=400,
            detail="Unable to determine client IP address"
        )
    
    client_ip = request.client.host
    if internal_endpoint_limiter.is_rate_limited(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Max 5 requests per 60 seconds."
        )
    
    # Require token in production or when INTERNAL_TEST_TOKEN is set
    if settings.SENTRY_ENVIRONMENT == "production":
        if not settings.INTERNAL_TEST_TOKEN:
            raise HTTPException(
                status_code=403,
                detail="Test endpoint disabled in production without INTERNAL_TEST_TOKEN"
            )
        if x_internal_token != settings.INTERNAL_TEST_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid or missing X-Internal-Token")
    elif settings.INTERNAL_TEST_TOKEN:
        # Token is configured in non-production, so require it
        if x_internal_token != settings.INTERNAL_TEST_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid or missing X-Internal-Token")
    
    raise ValueError("Sentry test exception — verify event appears in Sentry dashboard")


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
