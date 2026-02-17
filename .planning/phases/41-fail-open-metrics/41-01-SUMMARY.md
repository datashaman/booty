---
phase: 41-fail-open-metrics
plan: 01
subsystem: reviewer
tags: [metrics, fail-open, structlog]

requires:
  - phase: 40-promotion-gating
    provides: reviewer_check_success, promotion gate
provides:
  - reviewer/metrics.py with increment_reviewer_fail_open, get_reviewer_24h_stats
  - Runner fail-open path: check success, no comment, metrics incremented
affects: []

tech-stack:
  added: []
  patterns: [Architect-style metrics events, fail-open buckets]

key-files:
  created: [src/booty/reviewer/metrics.py]
  modified: [src/booty/reviewer/runner.py]

key-decisions:
  - "Fail-open buckets: diff_fetch_failed, github_api_failed, llm_timeout, llm_error, schema_parse_failed, unexpected_exception"

duration: ~8min
completed: 2026-02-17
---

# Phase 41 Plan 01: Fail-Open Handling Summary

**Reviewer metrics module and fail-open path: infra/LLM failure yields check success with "Reviewer unavailable (fail-open)", no PR comment, reviewer_fail_open incremented.**

## Performance

- **Duration:** ~8 min
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `src/booty/reviewer/metrics.py` mirroring architect pattern: get_reviewer_metrics_dir, events array, tempfile + os.replace atomic write
- Event types: total, blocked, suggestions, fail_open (with bucket)
- increment_reviewer_fail_open(fail_open_type), get_reviewer_24h_stats()
- Runner exception path: classify exception → increment_reviewer_fail_open → edit_check_run success, no post_reviewer_comment
- structlog reviewer_fail_open with repo, pr, sha, fail_open_type

## Task Commits

1. **Task 1: Create reviewer/metrics.py** - `32529f4` (feat)
2. **Task 2: Wire fail-open in runner.py** - `74419ad` (feat)

## Files Created/Modified

- `src/booty/reviewer/metrics.py` - Reviewer metrics persistence (events, 24h stats)
- `src/booty/reviewer/runner.py` - Fail-open exception handling, metrics, structlog

## Decisions Made

None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Ready for 41-02-PLAN.md (success-path metrics).

---
*Phase: 41-fail-open-metrics*
*Completed: 2026-02-17*
