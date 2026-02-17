---
phase: 34-output-failure-handling
plan: 03
subsystem: architect
tags: [architect, main, planner-worker]

requires:
  - phase: 34-output-failure-handling
    plan: 01
    provides: ArchitectPlan, build_architect_plan
  - phase: 34-output-failure-handling
    plan: 02
    provides: format_architect_section, format_plan_comment, update_plan_comment_with_architect_section, post_architect_blocked_comment
provides:
  - Architect flow with comment updates for approved/rewritten/blocked
affects: 35, 36

key-files:
  modified: [src/booty/main.py]

key-decisions:
  - "Approved/rewritten: post_plan_comment with full body; block: post_architect_blocked_comment (updates same comment)"
  - "status=rewritten when architect_notes contains 'ambiguous' or 'overreach'"

patterns-established:
  - "Comment update best-effort: try/except GithubException, log and continue"
  - "Block never enqueues Builder; no automatic retries"

duration: ~5min
completed: 2026-02-17
---

# Phase 34 Plan 03: main.py Architect Comment Updates Summary

**Planner worker wires Architect comment updates for approved, rewritten, and blocked outcomes**

## Performance

- **Duration:** ~5 min
- **Tasks:** 2
- **Files modified:** 1 (main.py)

## Accomplishments

- Approved: build_architect_plan, format_architect_section, format_plan_comment, post_plan_comment (find-and-edit)
- Rewritten: same flow; status=rewritten when notes contain "ambiguous" or "overreach"
- Blocked: extract reason from architect_notes, post_architect_blocked_comment(reason), add_architect_review_label; do NOT enqueue Builder
- Comment updates wrapped in try/except GithubException (best-effort)

## Task Commits

1. **Task 1 & 2: Update plan comment on approved, block flow** - single commit (feat)

## Files Created/Modified

- `src/booty/main.py` - _planner_worker_loop: Architect approved/rewritten/blocked comment flow

## Decisions Made

None - followed plan as specified

## Deviations from Plan

None - plan executed exactly as written

## Issues Encountered

None

## Next Phase Readiness

- Architect comment updates complete
- Phase 35 (Idempotency) can build on ArchitectPlan and comment structure

---
*Phase: 34-output-failure-handling*
*Completed: 2026-02-17*
