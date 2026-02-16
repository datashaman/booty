---
phase: 25-surfacing
plan: 01
subsystem: memory
tags: [memory, github, pr-comment, check-run, verifier]

# Dependency graph
requires:
  - phase: 24
    provides: memory.lookup.query
provides:
  - post_memory_comment (find-or-edit by <!-- booty-memory -->)
  - surface_pr_comment on Verifier check_run completion
  - format_matches_for_pr for PR display
affects: [25-02 Governor HOLD merge]

# Tech tracking
tech-stack:
  added: []
  patterns: [find-or-edit PR comment, check_run webhook for booty/verifier]

key-files:
  created: [src/booty/memory/surfacing.py]
  modified: [src/booty/github/comments.py, src/booty/webhooks.py, src/booty/memory/__init__.py]

key-decisions:
  - "Trigger on check_run completed (not pull_request) — Memory surfaces only after Verifier runs"

patterns-established:
  - "PR Memory comment: single updatable, marker <!-- booty-memory -->, zero matches = omit"

# Metrics
duration: ~15min
completed: 2026-02-16
---

# Phase 25 Plan 01: PR Comment Surfacing Summary

**PR comment "Memory: related history" on Verifier check completion — find-or-edit by marker, up to max_matches (configurable). MEM-19, MEM-20.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-16
- **Completed:** 2026-02-16
- **Tasks:** 4
- **Files modified:** 5

## Accomplishments

- post_memory_comment with find-or-edit by `<!-- booty-memory -->`, title "## Memory: related history"
- surface_pr_comment: format matches, run lookup, post only when matches (omit on zero)
- check_run webhook branch for booty/verifier: loads config, gets PR paths, surfaces comment
- Unit tests for format_matches_for_pr and surface_pr_comment

## Task Commits

1. **Task 1: post_memory_comment and format helper** - `80d65f4` (feat)
2. **Task 2: memory/surfacing.py format and surface_pr_comment** - `69af949` (feat)
3. **Task 3: check_run webhook handler** - `55cb2cd` (feat)
4. **Task 4: Tests** - `562f2e7` (test)

## Files Created/Modified

- `src/booty/github/comments.py` - post_memory_comment
- `src/booty/memory/surfacing.py` - format_matches_for_pr, surface_pr_comment
- `src/booty/memory/__init__.py` - export surface_pr_comment
- `src/booty/webhooks.py` - check_run handler
- `tests/test_memory_surfacing.py` - surfacing unit tests

## Decisions Made

None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

Ready for 25-02 (Governor HOLD surfacing) — reuses post_memory_comment, needs merge logic for Governor section.

---
*Phase: 25-surfacing*
*Completed: 2026-02-16*
