---
phase: 12-sentry-apm
plan: 02
subsystem: infra
tags: [sentry, capture_exception, error-tracking]

requires:
  - phase: 12-01
    provides: Sentry SDK init, FastAPI integration
provides:
  - capture_exception in job pipeline failure handler
  - capture_exception in verifier job failure handler
  - Verification test for capture_exception
  - GET /internal/sentry-test for manual E2E
affects: [13-observability-agent]

tech-stack:
  added: []
  patterns: [explicit-capture-handled-failures]

key-files:
  created: [tests/test_sentry_integration.py]
  modified: [src/booty/main.py]

key-decisions:
  - "Re-raise after capture in verifier so worker handles failure"

patterns-established:
  - "capture_exception before post_failure_comment in job handler"

duration: 10min
completed: 2026-02-15
---

# Phase 12 Plan 02: capture_exception — Summary

**Job and verifier failures explicitly captured in Sentry; pytest verifies capture; manual /internal/sentry-test route for E2E**

## Performance

- **Duration:** 10 min
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- sentry_sdk.capture_exception in process_job except block with job_id/issue_number tags
- try/except in _process_verifier_job with capture_exception, set_tag, re-raise
- test_process_job_capture_exception_on_pipeline_crash verifies capture on mocked pipeline crash
- GET /internal/sentry-test raises for manual Sentry E2E verification

## Task Commits

1. **Task 1: capture_exception in process_job** - `f9f1ac6` (feat)
2. **Task 2+3: capture_exception in verifier, sentry-test route** - `39a557e` (feat)
3. **Task 3: Verification test** - `cf90102` (test)

## Files Created/Modified
- `src/booty/main.py` - capture_exception in job/verifier, /internal/sentry-test route
- `tests/test_sentry_integration.py` - pytest verifies capture on pipeline crash

## Decisions Made
None - followed plan as specified

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
None beyond Plan 12-01 (Sentry DSN)

## Next Phase Readiness
- Phase 13 can wire Sentry webhook; errors now tracked with release correlation
- Manual E2E: hit GET /internal/sentry-test with SENTRY_DSN set, verify event in Sentry

---
*Phase: 12-sentry-apm*
*Completed: 2026-02-15*
