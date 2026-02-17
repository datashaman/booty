---
phase: 43-dedup-alignment
plan: 01
subsystem: dedup
tags: [verifier, security, router, dedup, multi-tenant]

# Dependency graph
requires:
  - phase: 42-event-router
    provides: Router with internal.full_name for PR events
provides:
  - VerifierQueue with repo-scoped dedup (repo_full_name, pr_number, head_sha)
  - SecurityQueue with repo-scoped dedup (repo_full_name, pr_number, head_sha)
  - Router passes internal.full_name to both queues
affects: [44-planner-architect-builder, 46-cancel-semantics]

key-files:
  created: []
  modified: [src/booty/verifier/queue.py, src/booty/security/queue.py, src/booty/router/router.py]

key-decisions: []

patterns-established:
  - "PR agent dedup: (repo_full_name, pr_number, head_sha) — same key format as ReviewerQueue"

# Metrics
duration: 5min
completed: 2026-02-17
---

# Phase 43 Plan 01: Verifier/Security Repo-Scoped Dedup Summary

**VerifierQueue and SecurityQueue use (repo_full_name, pr_number, head_sha) dedup; router passes internal.full_name. DEDUP-01, DEDUP-04.**

## Performance

- **Duration:** ~5 min
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- VerifierQueue: _dedup_key, is_duplicate, mark_processed, enqueue all accept/derive repo_full_name
- SecurityQueue: Same signature alignment
- Router: passes internal.full_name to verifier_queue.is_duplicate and security_queue.is_duplicate

## Task Commits

1. **Task 1: Update VerifierQueue dedup to include repo** - `a97b7e5` (feat)
2. **Task 2: Update SecurityQueue dedup to include repo** - `1ad4315` (feat, bundled with task 3)
3. **Task 3: Update router to pass repo_full_name** - `1ad4315` (feat)

## Files Created/Modified

- `src/booty/verifier/queue.py` - repo-scoped _dedup_key, is_duplicate, mark_processed, enqueue
- `src/booty/security/queue.py` - same
- `src/booty/router/router.py` - verifier/security is_duplicate calls use internal.full_name

## Decisions Made

None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

VerifierQueue and SecurityQueue aligned with ReviewerQueue. Ready for 43-02 (dedup documentation).

---
*Phase: 43-dedup-alignment*
*Completed: 2026-02-17*
