---
phase: 18-security-foundation-check
plan: 03
subsystem: security
tags: [webhooks, pull_request, lifespan, security_queue]

# Dependency graph
requires:
  - phase: 18-02
    provides: SecurityJob, SecurityQueue, process_security_job
provides:
  - pull_request → SecurityJob enqueue
  - security_queue in app lifespan
affects: [phases 19-21]

# Tech tracking
tech-stack:
  added: []
  patterns: [Verifier+Security parallel webhook handling]

key-files:
  created: []
  modified: [src/booty/webhooks.py, src/booty/main.py]

key-decisions:
  - "Security runs on every PR (no is_agent_pr filter)"
  - "Both Verifier and Security can run; return ignored only when both disabled"

patterns-established:
  - "pull_request opened/synchronize/reopened triggers both Verifier and Security"

# Metrics
duration: 5min
completed: 2026-02-16
---

# Phase 18 Plan 03: pull_request Webhook & Lifespan Summary

**pull_request opened/synchronize/reopened enqueues SecurityJob; security_queue started in lifespan when security_enabled**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-16
- **Completed:** 2026-02-16
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- pull_request handler enqueues SecurityJob to security_queue when security_enabled
- Security runs on every PR (no is_agent_pr filter)
- security_queue created and workers started in lifespan when security_enabled
- _process_security_job wrapper with exception handling
- Return "ignored" only when both Verifier and Security disabled

## Task Commits

1. **Task 1: Wire pull_request to Security enqueue** - `ff21d8b` (feat)
2. **Task 2: Add security_queue to lifespan** - `10aba3a` (feat)

**Plan metadata:** (pending)

## Files Created/Modified

- `src/booty/webhooks.py` - Security enqueue in pull_request block
- `src/booty/main.py` - security_queue, SECURITY_WORKER_COUNT, lifespan

## Decisions Made

None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 18 complete. Security foundation ready for Phases 19–21 (secrets, vulns, permission drift).

---
*Phase: 18-security-foundation-check*
*Completed: 2026-02-16*
