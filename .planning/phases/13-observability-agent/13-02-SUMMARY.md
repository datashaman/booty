---
phase: 13-observability-agent
plan: 02
subsystem: observability
tags: [sentry, github, tenacity, pygithub]

requires:
  - phase: 13-01
    provides: Sentry webhook route, HMAC verification, filters
provides:
  - GitHub issue creation from Sentry events with agent:builder label
  - Issue body: severity, release, environment, Sentry link, stack, breadcrumbs
  - Retry 3x exponential backoff; spool to JSONL on failure
affects: Builder (picks up created issues)

tech-stack:
  added: []
  patterns: [tenacity retry on 5xx only, disk spool for failed API calls]

key-files:
  created: [src/booty/github/issues.py]
  modified: [src/booty/webhooks.py, src/booty/github/__init__.py, src/booty/config.py]

key-decisions:
  - "Retry only on 5xx; 4xx (auth, not found) not retried"
  - "OBSV_SPOOL_PATH env for spool location; /tmp default"

patterns-established:
  - "create_sentry_issue_with_retry wraps tenacity + spool"

duration: 15min
completed: 2026-02-15
---

# Phase 13 Plan 02: Issue Creation from Sentry Summary

**GitHub issue creation with agent:builder label, retry, and disk spool**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-02-15
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- build_sentry_issue_title, build_sentry_issue_body per CONTEXT format
- create_issue_from_sentry_event with PyGithub
- Retry 3x with exponential backoff (2s, 8s, 30s); 5xx only
- _spool_failed_sentry_event to JSONL
- sentry_webhook wires to create_sentry_issue_with_retry

## Task Commits

1. **Task 1: Issue body builder and create_issue_from_sentry_event** - `b1d9af0` (feat)
2. **Task 2: Retry and spool** - included in b1d9af0
3. **Task 3: Wire into sentry_webhook** - `9c23bb9` (feat)

## Files Created/Modified
- `src/booty/github/issues.py` - new module
- `src/booty/webhooks.py` - import and call create_sentry_issue_with_retry
- `src/booty/github/__init__.py` - export issues functions
- `src/booty/config.py` - Sentry section reorder

## Decisions Made
- Retry only on 5xx; 4xx not retried
- OBSV_SPOOL_PATH via env, default /tmp/booty-sentry-spool.jsonl

## Deviations from Plan

None - plan executed as written.

## Issues Encountered
None

## Next Phase Readiness
- Phase 13 complete; alert-to-issue pipeline end-to-end

---
*Phase: 13-observability-agent*
*Completed: 2026-02-15*
