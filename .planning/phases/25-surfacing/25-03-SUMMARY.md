---
phase: 25-surfacing
plan: 03
subsystem: memory
tags: [memory, observability, sentry, issue-body]

# Dependency graph
requires:
  - phase: 24
    provides: memory.lookup.query
  - phase: (Observability)
    provides: build_sentry_issue_body
provides:
  - build_related_history_for_incident
  - build_sentry_issue_body related_history param
  - Observability incident "Related history" section
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [related_history injection after Sentry link, before Location]

key-files:
  created: []
  modified: [src/booty/github/issues.py, src/booty/memory/surfacing.py, src/booty/webhooks.py]

key-decisions:
  - "related_history param on build_sentry_issue_body — caller provides full markdown"

patterns-established:
  - "Sentry webhook: build related_history before create, pass to create_sentry_issue_with_retry"

# Metrics
duration: ~12min
completed: 2026-02-16
---

# Phase 25 Plan 03: Observability Incident Surfacing Summary

**Incident issue "Related history" section — build_sentry_issue_body related_history param, build_related_history_for_incident, wire Sentry webhook. MEM-22.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-02-16
- **Completed:** 2026-02-16
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments

- build_sentry_issue_body(..., related_history=None) — insert after Sentry link, before Location
- build_related_history_for_incident: paths from stack frames/culprit/metadata, lookup, format
- create_issue_from_sentry_event and create_sentry_issue_with_retry accept related_history
- Sentry webhook: load config, build_related_history_for_incident when enabled, pass to create
- Unit tests for build_related_history_for_incident and build_sentry_issue_body placement

## Task Commits

1. **Task 1: build_sentry_issue_body related_history param** - `7f9ab52` (feat)
2. **Task 2: build_related_history_for_incident** - `8d8adf1` (feat)
3. **Task 3: Wire Observability webhook** - `6a1bb9e` (feat)
4. **Task 4: Tests** - `8b0a986` (test)

## Files Created/Modified

- `src/booty/github/issues.py` - build_sentry_issue_body, create_issue_from_sentry_event, create_sentry_issue_with_retry
- `src/booty/memory/surfacing.py` - build_related_history_for_incident
- `src/booty/webhooks.py` - Sentry handler passes related_history
- `tests/test_memory_surfacing.py` - incident surfacing tests

## Decisions Made

None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

Phase 25 Surfacing complete. Ready for Phase 26 CLI.

---
*Phase: 25-surfacing*
*Completed: 2026-02-16*
