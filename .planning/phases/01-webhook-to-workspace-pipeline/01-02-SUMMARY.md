---
phase: 01-webhook-to-workspace-pipeline
plan: 02
subsystem: api
tags: [fastapi, webhooks, github, async, gitpython, structlog, hmac]

# Dependency graph
requires:
  - phase: 01-01
    provides: Pydantic Settings config and structlog JSON logging foundation

provides:
  - GitHub webhook endpoint with HMAC signature verification
  - Async job queue with worker pool and idempotency
  - Repository cloning to isolated temporary workspaces
  - Event filtering and duplicate delivery prevention
  - Structured JSON logging with correlation IDs

affects: [02-llm-powered-code-generation, 03-pr-creation-workflow]

# Tech tracking
tech-stack:
  added: [asgi-correlation-id]
  patterns: [async context managers, executor for blocking I/O, lifespan handlers]

key-files:
  created:
    - src/booty/jobs.py
    - src/booty/repositories.py
    - src/booty/webhooks.py
    - src/booty/main.py
  modified: []

key-decisions:
  - "HMAC verification before any processing for security"
  - "Delivery ID tracking with 10k cap for memory efficiency"
  - "Clone operations run in executor to avoid blocking event loop"
  - "Feature branch naming: agent/issue-{number}"
  - "Job ID format: {issue_number}-{delivery_id}"

patterns-established:
  - "Async context managers for resource lifecycle (workspace cleanup)"
  - "Blocking I/O wrapped in loop.run_in_executor()"
  - "Structlog with bound context (job_id, worker_id, issue_number)"
  - "FastAPI lifespan pattern for startup/shutdown"
  - "Job queue stored in app.state for access from routes"

# Metrics
duration: 3min
completed: 2026-02-14
---

# Phase 01 Plan 02: Webhook Handler and Job Queue Summary

**FastAPI webhook receiver with HMAC verification, async job queue with workers, and isolated git workspace cloning**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-14T19:09:54Z
- **Completed:** 2026-02-14T19:12:26Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Webhook handler validates GitHub HMAC signatures and filters events (issues + labeled + trigger label)
- Async job queue with worker pool processes jobs without blocking webhook responses
- Repository cloning to isolated temp directories with automatic cleanup and feature branch creation
- Duplicate delivery detection prevents processing same webhook twice
- All operations produce structured JSON logs with correlation IDs

## Task Commits

Each task was committed atomically:

1. **Task 1: Job queue with state tracking and idempotency** - `0da8220` (feat)
2. **Task 2: Repository manager with fresh clone and cleanup** - `96c7cfd` (feat)
3. **Task 3: Webhook endpoint and FastAPI app assembly** - `ef5c0ab` (feat)

## Files Created/Modified
- `src/booty/jobs.py` - Job model, JobState enum, JobQueue with async workers
- `src/booty/repositories.py` - prepare_workspace context manager, git cloning with feature branches
- `src/booty/webhooks.py` - GitHub webhook route with HMAC verification and event filtering
- `src/booty/main.py` - FastAPI app with correlation middleware, lifespan management, health check

## Decisions Made

**HMAC verification before JSON parsing**: Raw body must be read first for signature validation - critical security requirement.

**Delivery ID deduplication with 10k cap**: Set-based tracking with deque for ordering prevents unbounded memory growth while handling realistic webhook volumes.

**Executor for git clone**: GitPython is synchronous/blocking I/O - must run in executor to avoid blocking async event loop.

**Feature branch naming convention**: `agent/issue-{number}` provides clear identification and avoids conflicts.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed git.Repo.clone_from positional argument**
- **Found during:** Task 2 verification
- **Issue:** GitPython clone_from doesn't accept branch as positional arg - AttributeError on 'str' object
- **Fix:** Wrapped clone in lambda with branch as keyword argument: `git.Repo.clone_from(url, path, branch=branch)`
- **Files modified:** src/booty/repositories.py
- **Verification:** Test clone succeeded with correct branch checkout
- **Committed in:** 96c7cfd (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Fix necessary to unblock task verification. No scope creep.

## Issues Encountered
None - plan executed smoothly after fixing GitPython API usage.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 2 (LLM-powered code generation):**
- Webhook pipeline delivers isolated workspaces with feature branches
- Job queue provides async processing with state tracking
- Correlation IDs enable request tracing through entire pipeline
- process_job() placeholder ready for LLM integration

**Integration points for Phase 2:**
- Replace process_job() placeholder with LLM prompt construction and code generation
- Workspace object provides repo, path, and branch for file manipulation
- Job payload contains issue title, body, and labels for prompt context

**No blockers or concerns.**

---
*Phase: 01-webhook-to-workspace-pipeline*
*Completed: 2026-02-14*
