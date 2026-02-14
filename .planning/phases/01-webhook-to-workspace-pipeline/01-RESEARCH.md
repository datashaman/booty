# Phase 01: Webhook-to-Workspace Pipeline - Research

**Researched:** 2026-02-14
**Domain:** FastAPI webhooks, async job processing, Git repository management, structured logging
**Confidence:** HIGH

## Summary

Phase 01 implements a webhook-to-workspace pipeline for receiving GitHub webhook events and preparing isolated workspaces. The standard approach uses FastAPI for webhook handling with HMAC signature verification, Pydantic Settings for configuration, asyncio.Queue or BackgroundTasks for async job execution, GitPython for repository cloning, and structlog for structured JSON logging with correlation IDs.

The core pattern is: (1) FastAPI receives webhook and validates HMAC signature, (2) returns 200/202 immediately while enqueuing job, (3) background worker processes job in isolated temp directory, (4) all operations logged with correlation IDs for traceability. This architecture ensures webhooks respond within GitHub's 10-second timeout while heavy processing happens asynchronously.

**Primary recommendation:** Use FastAPI 0.129+ with Pydantic 2.0+ for webhook handling, Python's built-in asyncio.Queue for simple in-memory job queuing, GitPython 3.1.46 for repository operations, structlog 25.5+ with asgi-correlation-id for JSON logging, and tempfile.TemporaryDirectory for workspace isolation.

## Standard Stack

The established libraries/tools for this domain:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.129+ | Webhook HTTP endpoint | Industry standard for Python APIs, built-in async support, automatic validation, OpenAPI docs |
| Pydantic | 2.0+ | Configuration validation | Type-safe settings management, environment variable parsing, built-in with FastAPI |
| pydantic-settings | 2.0+ | Environment config loading | Official Pydantic extension for BaseSettings, supports .env files and nested configs |
| GitPython | 3.1.46 | Repository cloning/branching | Standard Python wrapper for Git operations, mature and widely used |
| structlog | 25.5+ | Structured JSON logging | Processor-based logging with context binding, industry standard for cloud-native apps |
| uvicorn | Latest | ASGI server | Official FastAPI recommendation, async-native, production-ready with Gunicorn |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asgi-correlation-id | Latest | Correlation ID middleware | Automatic request ID tracking across async operations |
| python-multipart | Latest | Form data parsing | Required for FastAPI to receive webhook payloads |
| hmac | stdlib | HMAC signature verification | GitHub webhook signature validation (built-in) |
| hashlib | stdlib | SHA256 hashing | Used with hmac for signature computation (built-in) |
| tempfile | stdlib | Temporary directories | Isolated workspace creation with auto-cleanup (built-in) |
| asyncio | stdlib | Async job queue | In-memory task queue via asyncio.Queue (built-in) |
| contextvars | stdlib | Context propagation | Correlation ID propagation in async code (built-in) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.Queue | Celery + Redis | Celery adds complexity (RabbitMQ/Redis) but enables distributed processing, task persistence, and retries across servers - overkill for single-server Phase 01 |
| FastAPI BackgroundTasks | asyncio.Queue | BackgroundTasks simpler but no job state tracking; Queue enables pending/running/completed tracking required by REQ-05 |
| structlog | stdlib logging | stdlib logging requires manual JSON formatting and context management; structlog is cloud-native standard |
| tempfile | shutil + custom cleanup | tempfile provides automatic cleanup and security best practices; custom solution error-prone |

**Installation:**
```bash
pip install fastapi[standard] pydantic-settings gitpython structlog asgi-correlation-id
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── config/              # Pydantic settings with environment validation
├── webhooks/            # FastAPI webhook routes and signature verification
├── jobs/                # Job state tracking and async queue management
├── repositories/        # GitPython repository cloning and branch operations
└── logging/             # structlog configuration with correlation IDs
```

### Pattern 1: Webhook Handler with Immediate Response

**What:** Receive webhook, validate signature, enqueue job, return 200 OK immediately

**When to use:** GitHub has 10-second timeout; all webhook processing must return quickly

**Example:**
```python
# Source: https://fastapi.tiangolo.com/tutorial/background-tasks/
# Source: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
import hmac
import hashlib

app = FastAPI()

async def verify_signature(payload_body: bytes, secret: str, signature_header: str):
    """Verify GitHub webhook HMAC signature using constant-time comparison."""
    hash_object = hmac.new(
        secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=403, detail="Invalid signature")

@app.post("/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    # Read raw body for signature verification
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    # Verify signature (raises 403 if invalid)
    await verify_signature(body, settings.WEBHOOK_SECRET, signature)

    # Parse JSON payload
    payload = await request.json()

    # Enqueue job asynchronously
    background_tasks.add_task(process_webhook, payload)

    # Return immediately (within GitHub's 10-second timeout)
    return {"status": "accepted"}
```

### Pattern 2: Async Job Queue with State Tracking

**What:** Use asyncio.Queue for in-memory job queue with state tracking (queued/running/completed/failed)

**When to use:** REQ-05 requires async execution with job state tracking; simple single-server deployment

**Example:**
```python
# Source: https://docs.python.org/3/library/asyncio-queue.html
# Source: https://testdriven.io/blog/developing-an-asynchronous-task-queue-in-python/

import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import Dict

class JobState(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Job:
    job_id: str
    issue_url: str
    payload: dict
    state: JobState = JobState.QUEUED

class JobQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.jobs: Dict[str, Job] = {}

    async def enqueue(self, job: Job):
        """Add job to queue (idempotent on job_id)."""
        if job.job_id in self.jobs:
            return  # Duplicate - REQ-02 idempotency
        self.jobs[job.job_id] = job
        await self.queue.put(job)

    async def worker(self):
        """Process jobs from queue."""
        while True:
            job = await self.queue.get()
            job.state = JobState.RUNNING
            try:
                await process_job(job)
                job.state = JobState.COMPLETED
            except Exception:
                job.state = JobState.FAILED
            finally:
                self.queue.task_done()
```

### Pattern 3: Fresh Workspace with Automatic Cleanup

**What:** Clone repository to temporary directory with context manager cleanup

**When to use:** REQ-03 requires fresh isolation per job; prevents state leakage between jobs

**Example:**
```python
# Source: https://docs.python.org/3/library/tempfile.html
# Source: https://gitpython.readthedocs.io/en/stable/tutorial.html

import tempfile
from git import Repo

async def process_job_with_workspace(job: Job):
    """Process job in isolated temporary workspace."""
    # Context manager ensures cleanup even on exceptions
    with tempfile.TemporaryDirectory() as workspace:
        # Clone repository to temporary directory
        repo = Repo.clone_from(
            settings.TARGET_REPO_URL,
            workspace,
            branch=settings.TARGET_BRANCH
        )

        # Create feature branch
        feature_branch = repo.create_head(f"agent-builder-{job.job_id}")
        feature_branch.checkout()

        # Do work in isolated workspace
        # ... (code generation happens here)

    # Workspace automatically cleaned up here
```

### Pattern 4: Structured Logging with Correlation IDs

**What:** Use structlog + asgi-correlation-id for JSON logs with request tracing

**When to use:** REQ-06 requires correlation IDs linking webhook → job → actions

**Example:**
```python
# Source: https://betterstack.com/community/guides/logging/structlog/
# Source: https://github.com/snok/asgi-correlation-id

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI

# Configure structlog for production
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)

# Usage in webhook handler
logger = structlog.get_logger()

async def process_webhook(payload: dict):
    # Correlation ID automatically included from middleware
    logger.info("webhook_received",
                issue_number=payload["issue"]["number"],
                action=payload["action"])
```

### Pattern 5: Pydantic Settings for Configuration

**What:** Type-safe configuration with environment variable parsing

**When to use:** REQ-04 requires configurable repo/branch/label; REQ-17 requires deterministic config

**Example:**
```python
# Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
# Source: https://fastapi.tiangolo.com/advanced/settings/

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # GitHub webhook configuration
    WEBHOOK_SECRET: str
    TARGET_REPO_URL: str
    TARGET_BRANCH: str = "main"
    TRIGGER_LABEL: str = "agent:builder"

    # LLM configuration (REQ-17 deterministic)
    LLM_TEMPERATURE: float = 0.0
    LLM_MODEL: str = "claude-sonnet-4"
    LLM_TIMEOUT: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

settings = Settings()
```

### Anti-Patterns to Avoid

- **Using == for signature comparison:** Timing attacks can leak signature bytes; always use `hmac.compare_digest()` for constant-time comparison
- **Blocking webhook response:** GitHub times out after 10 seconds; never clone repos or call LLMs in webhook handler - enqueue and return immediately
- **Shared workspace directories:** Reusing directories leaks state between jobs; always use fresh `tempfile.TemporaryDirectory()` per job
- **Plain text logging:** Cloud platforms expect JSON logs; use structlog with JSONRenderer, not print() or basic logging
- **Hardcoded configuration:** REQ-04/REQ-17 require configurability; use Pydantic Settings, not hardcoded values

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HMAC signature validation | Custom hash comparison | `hmac.compare_digest()` | Timing attacks can leak secrets via response-time side channels; constant-time comparison prevents this |
| Correlation ID propagation | Thread-local storage | `contextvars.ContextVar` + asgi-correlation-id | Thread-locals don't work with async; contextvars preserves context across awaits |
| JSON logging | Manual dict serialization | structlog with JSONRenderer | Edge cases (exceptions, datetime, nested context) require complex handling; structlog handles all |
| Temporary directory cleanup | `os.makedirs()` + `shutil.rmtree()` | `tempfile.TemporaryDirectory()` | Cleanup failures (permissions, open files) cause leaks; tempfile handles edge cases |
| Background task queue | Custom threading | asyncio.Queue or BackgroundTasks | Race conditions, deadlocks, resource leaks are hard; asyncio.Queue is battle-tested |
| Environment config parsing | `os.getenv()` + manual parsing | pydantic-settings | Type coercion, validation, defaults, .env files need custom code; Pydantic does it all |
| Webhook idempotency | Manual deduplication | Hash of (issue_url + event_timestamp) | Replay attacks and race conditions are subtle; need atomic check-and-set with proper key |

**Key insight:** Webhook security, async task management, and context propagation have subtle edge cases (timing attacks, race conditions, cleanup failures) that are easy to get wrong. Use battle-tested libraries that handle these correctly.

## Common Pitfalls

### Pitfall 1: Signature Validation with Raw Body

**What goes wrong:** Parsing JSON before signature validation fails because HMAC is computed over raw bytes, not parsed JSON

**Why it happens:** Natural to parse JSON first, but `await request.json()` consumes body stream and changes byte representation

**How to avoid:** Always read raw body with `await request.body()` before parsing JSON; validate signature on raw bytes

**Warning signs:** Signature validation always fails even with correct secret; signatures work in testing but fail in production

### Pitfall 2: GitHub API Eventual Consistency

**What goes wrong:** Processing webhook immediately after receiving it can see stale GitHub API state (issue not yet created/labeled)

**Why it happens:** GitHub webhooks fire before API reaches consistency across all servers

**How to avoid:** Add 1-second delay before processing webhook events (common practice in GitHub webhook handlers)

**Warning signs:** Intermittent 404s when fetching issue details; label appears in webhook but not in API response

### Pitfall 3: Temporary Directory Cleanup on Windows

**What goes wrong:** `TemporaryDirectory` cleanup fails with PermissionError on Windows when Git creates read-only files (.git directory)

**Why it happens:** Git sets files read-only; Windows can't delete read-only files; tempfile cleanup doesn't handle this

**How to avoid:** Use `ignore_cleanup_errors=True` on Windows, or implement custom cleanup with `onerror` handler to change permissions before deletion

**Warning signs:** Tests pass on macOS/Linux but fail on Windows; ResourceWarning about unclosed directory handles

### Pitfall 4: Webhook Replay Attacks

**What goes wrong:** Attacker intercepts valid webhook delivery and replays it, triggering duplicate processing

**Why it happens:** HMAC signature is valid for replayed payloads; need additional uniqueness check

**How to avoid:** Use `X-GitHub-Delivery` header as idempotency key (unique per delivery); store processed delivery IDs in job queue

**Warning signs:** Same webhook processed multiple times; duplicate PRs created for single issue

### Pitfall 5: Background Task Memory Leaks

**What goes wrong:** Using FastAPI `BackgroundTasks` for long-running jobs causes memory buildup when jobs accumulate faster than they complete

**Why it happens:** BackgroundTasks has no queue size limit; unbounded growth if webhook rate > processing rate

**How to avoid:** Use asyncio.Queue with bounded maxsize (e.g., 100); webhook returns 503 if queue full (backpressure)

**Warning signs:** Memory usage grows over time; server OOM kills under load; response times degrade

### Pitfall 6: Context Variable Middleware Ordering

**What goes wrong:** Correlation IDs missing from logs when CorrelationIdMiddleware added after logging middleware

**Why it happens:** FastAPI middleware executes in reverse order of add_middleware() calls; logging happens before correlation ID set

**How to avoid:** Add CorrelationIdMiddleware first (before any logging middleware); verify middleware order in docs

**Warning signs:** Correlation IDs present in some logs but not others; logs within same request have different IDs

### Pitfall 7: GitPython Resource Cleanup

**What goes wrong:** GitPython Repo objects hold file handles; not closing repos can exhaust file descriptors

**Why it happens:** Repo objects don't implement context manager protocol; GC cleanup is non-deterministic

**How to avoid:** Explicitly call `repo.close()` when done, or rely on tempfile cleanup to remove entire directory

**Warning signs:** "Too many open files" error after processing many jobs; file descriptor count grows over time

## Code Examples

Verified patterns from official sources:

### Complete Webhook Handler with Idempotency

```python
# Source: https://fastapi.tiangolo.com/tutorial/background-tasks/
# Source: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries

from fastapi import FastAPI, Request, HTTPException, Header
from typing import Optional
import hmac
import hashlib
import structlog

app = FastAPI()
logger = structlog.get_logger()

# Idempotency tracking (REQ-02)
processed_deliveries = set()

@app.post("/webhooks/github", status_code=200)
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
):
    # Read raw body for signature verification
    body = await request.body()

    # Verify HMAC signature (constant-time comparison)
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Missing signature")

    hash_object = hmac.new(
        settings.WEBHOOK_SECRET.encode('utf-8'),
        msg=body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()

    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Check idempotency (REQ-02)
    if x_github_delivery in processed_deliveries:
        logger.info("duplicate_webhook_delivery", delivery_id=x_github_delivery)
        return {"status": "already_processed"}

    # Parse payload
    payload = await request.json()

    # Filter for labeled events on issues
    if x_github_event != "issues" or payload.get("action") != "labeled":
        return {"status": "ignored"}

    if payload["label"]["name"] != settings.TRIGGER_LABEL:
        return {"status": "ignored"}

    # Mark as processed
    processed_deliveries.add(x_github_delivery)

    # Enqueue job
    job = Job(
        job_id=f"{payload['issue']['number']}-{x_github_delivery}",
        issue_url=payload["issue"]["html_url"],
        payload=payload
    )
    await job_queue.enqueue(job)

    logger.info("webhook_enqueued",
                job_id=job.job_id,
                issue_number=payload["issue"]["number"])

    return {"status": "accepted", "job_id": job.job_id}
```

### Repository Clone with Branch Creation

```python
# Source: https://gitpython.readthedocs.io/en/stable/tutorial.html

import tempfile
from git import Repo
import structlog

logger = structlog.get_logger()

async def clone_and_prepare_workspace(job: Job) -> str:
    """Clone repository and create feature branch in temporary directory."""

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as workspace:
        logger.info("cloning_repository",
                    workspace=workspace,
                    job_id=job.job_id)

        # Clone repository (REQ-03 fresh clone)
        repo = Repo.clone_from(
            settings.TARGET_REPO_URL,
            workspace,
            branch=settings.TARGET_BRANCH
        )

        # Create feature branch
        branch_name = f"agent-builder-issue-{job.payload['issue']['number']}"
        feature_branch = repo.create_head(branch_name)

        # Checkout the branch (mimics git checkout)
        repo.head.reference = feature_branch
        repo.head.reset(index=True, working_tree=True)

        logger.info("workspace_ready",
                    branch=branch_name,
                    workspace=workspace)

        # Do work here...

        # Cleanup happens automatically when exiting context
```

### Structlog Configuration for Production

```python
# Source: https://betterstack.com/community/guides/logging/structlog/
# Source: https://github.com/snok/asgi-correlation-id

import structlog
from asgi_correlation_id import CorrelationIdMiddleware, correlation_id

def configure_logging():
    """Configure structlog for production JSON logging with correlation IDs."""

    structlog.configure(
        processors=[
            # Merge in correlation ID from context
            structlog.contextvars.merge_contextvars,
            # Filter by log level
            structlog.stdlib.filter_by_level,
            # Add timestamp in ISO format
            structlog.processors.TimeStamper(fmt="iso"),
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Add log level
            structlog.stdlib.add_log_level,
            # Render stack info for exceptions
            structlog.processors.StackInfoRenderer(),
            # Format exception info
            structlog.processors.format_exc_info,
            # Output as JSON
            structlog.processors.JSONRenderer(),
        ],
        # Use stdlib logging factory for compatibility
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache loggers for performance
        cache_logger_on_first_use=True,
    )

# Add middleware to FastAPI app (must be first)
app.add_middleware(CorrelationIdMiddleware)

# Usage
logger = structlog.get_logger()
logger.info("event_name", key1="value1", key2="value2")
```

### Async Job Queue with Worker

```python
# Source: https://docs.python.org/3/library/asyncio-queue.html

import asyncio
from typing import Dict
import structlog

logger = structlog.get_logger()

class JobQueue:
    def __init__(self, maxsize: int = 100):
        self.queue = asyncio.Queue(maxsize=maxsize)
        self.jobs: Dict[str, Job] = {}
        self.workers = []

    async def start_workers(self, num_workers: int = 3):
        """Start background worker tasks."""
        for i in range(num_workers):
            worker = asyncio.create_task(self.worker(i))
            self.workers.append(worker)

    async def enqueue(self, job: Job):
        """Enqueue job (idempotent on job_id)."""
        if job.job_id in self.jobs:
            logger.info("duplicate_job", job_id=job.job_id)
            return

        self.jobs[job.job_id] = job
        job.state = JobState.QUEUED

        try:
            # Put with timeout to prevent blocking
            await asyncio.wait_for(self.queue.put(job), timeout=1.0)
            logger.info("job_enqueued", job_id=job.job_id)
        except asyncio.TimeoutError:
            logger.error("queue_full", job_id=job.job_id)
            raise

    async def worker(self, worker_id: int):
        """Process jobs from queue."""
        logger.info("worker_started", worker_id=worker_id)

        while True:
            try:
                job = await self.queue.get()
                job.state = JobState.RUNNING

                logger.info("job_started",
                           job_id=job.job_id,
                           worker_id=worker_id)

                try:
                    await process_job(job)
                    job.state = JobState.COMPLETED
                    logger.info("job_completed", job_id=job.job_id)
                except Exception as e:
                    job.state = JobState.FAILED
                    logger.error("job_failed",
                                job_id=job.job_id,
                                error=str(e))
                finally:
                    self.queue.task_done()
            except Exception as e:
                logger.error("worker_error",
                            worker_id=worker_id,
                            error=str(e))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 BaseSettings | Pydantic v2 + pydantic-settings package | 2023 (Pydantic 2.0) | Settings split into separate package; v1 deprecated in FastAPI 0.100+ |
| Thread-local storage | contextvars.ContextVar | Python 3.7 (2018) | Context variables work correctly with async/await; thread-locals leak across tasks |
| X-Hub-Signature (SHA1) | X-Hub-Signature-256 (SHA256) | GitHub 2020 | SHA256 is cryptographically stronger; SHA1 deprecated but still sent for legacy |
| Manual JSON logging | structlog with processors | ~2019 | Processor pipeline enables rich context, filtering, and formatting; manual JSON error-prone |
| Celery for all background tasks | FastAPI BackgroundTasks or asyncio.Queue | FastAPI 0.60+ (2020) | Simple tasks don't need distributed queue; BackgroundTasks/asyncio simpler for single-server |

**Deprecated/outdated:**
- **Pydantic v1 BaseSettings:** Deprecated in FastAPI 0.100+; Pydantic team stopped supporting v1 for Python 3.14+; use pydantic-settings 2.0+
- **X-Hub-Signature header:** GitHub deprecated HMAC-SHA1 in favor of HMAC-SHA256; use X-Hub-Signature-256 instead
- **Threading for async tasks:** Thread-local storage doesn't preserve context across awaits; use contextvars for correlation IDs

## Open Questions

Things that couldn't be fully resolved:

1. **Job State Persistence**
   - What we know: In-memory asyncio.Queue loses state on server restart
   - What's unclear: Whether Phase 01 needs job state persistence or if ephemeral state is acceptable
   - Recommendation: Start with in-memory (simpler); add Redis/database persistence in later phase if needed

2. **Idempotency Storage Duration**
   - What we know: `X-GitHub-Delivery` IDs should be stored to prevent replay attacks
   - What's unclear: How long to retain delivery IDs (memory vs disk, TTL policy)
   - Recommendation: Use in-memory set with max size (e.g., 10k entries); Phase 01 won't have high volume

3. **Worker Concurrency Limits**
   - What we know: Multiple workers can process jobs concurrently using asyncio.Queue
   - What's unclear: Optimal worker count for git clone + LLM operations (CPU vs I/O bound mix)
   - Recommendation: Start with 3 workers; tune based on observed CPU/memory/latency metrics

4. **GitHub API Rate Limiting**
   - What we know: GitHub API has rate limits (5000/hour authenticated)
   - What's unclear: Whether Phase 01 needs rate limit tracking or if it's deferred to later phases
   - Recommendation: Log API calls; add rate limit handling in Phase 02 when making more API calls

## Sources

### Primary (HIGH confidence)

- [FastAPI Background Tasks (Official)](https://fastapi.tiangolo.com/tutorial/background-tasks/) - Background task pattern
- [Pydantic Settings Documentation (Official)](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - Configuration management
- [GitHub Webhook Validation (Official)](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries) - HMAC signature verification
- [GitPython Tutorial (Official)](https://gitpython.readthedocs.io/en/stable/tutorial.html) - Repository cloning and branching
- [Python tempfile Documentation (Official)](https://docs.python.org/3/library/tempfile.html) - Temporary directory management
- [Python asyncio.Queue Documentation (Official)](https://docs.python.org/3/library/asyncio-queue.html) - Async job queue
- [Python contextvars Documentation (Official)](https://docs.python.org/3/library/contextvars.html) - Context variable propagation

### Secondary (MEDIUM confidence)

- [Better Stack: Structlog Guide](https://betterstack.com/community/guides/logging/structlog/) - Production structlog configuration
- [asgi-correlation-id GitHub](https://github.com/snok/asgi-correlation-id) - Correlation ID middleware for FastAPI
- [TestDriven.io: Async Task Queue](https://testdriven.io/blog/developing-an-asynchronous-task-queue-in-python/) - Job queue patterns
- [GitHub: Best Practices for Webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks) - Security and pitfalls
- [Hookdeck: GitHub Webhooks Guide](https://hookdeck.com/webhooks/platforms/guide-github-webhooks-features-and-best-practices) - Best practices
- [FastAPI Deployment with Uvicorn](https://fastapi.tiangolo.com/deployment/server-workers/) - Production deployment

### Tertiary (LOW confidence)

- [Medium: FastAPI Webhooks](https://www.getorchestra.io/guides/fast-api-webhooks-a-comprehensive-guide) - General webhook patterns
- [Svix: FastAPI Webhooks](https://www.svix.com/guides/receiving/receive-webhooks-with-python-fastapi/) - Webhook receiving patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified from official PyPI and documentation; version numbers confirmed
- Architecture: HIGH - Patterns sourced from official FastAPI, GitHub, and Python documentation
- Pitfalls: HIGH - Security issues documented in GitHub official docs; async pitfalls from Python stdlib docs

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (30 days - stable ecosystem, infrequent breaking changes)
