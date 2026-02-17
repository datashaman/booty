---
phase: 34-output-failure-handling
plan: 02
subsystem: architect
tags: [architect, github, comments]

requires:
  - phase: 34-output-failure-handling
    plan: 01
    provides: ArchitectPlan, build_architect_plan
provides:
  - format_architect_section(status, risk_level?, reason?, architect_notes?, rewrite_summary?)
  - format_plan_comment(plan, architect_section?)
  - update_plan_comment_with_architect_section
  - post_architect_blocked_comment(reason?) — updates same comment, fallback to new
affects: 34-03

key-files:
  modified: [src/booty/architect/output.py, src/booty/planner/output.py, src/booty/github/comments.py]

key-decisions:
  - "Block updates same plan comment; fallback to new only when no plan comment found"
  - "format_architect_section: Approved/Rewritten/Blocked variants with booty-architect wrapper"

patterns-established:
  - "booty-architect section between Builder instructions and <details>"
  - "update_plan_comment_with_architect_section finds <!-- booty-plan -->, injects or replaces section"

duration: ~8min
completed: 2026-02-17
---

# Phase 34 Plan 02: format_architect_section & Comment Update Summary

**booty-architect section formatting, plan comment update, block updates same comment**

## Performance

- **Duration:** ~8 min
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- format_architect_section(approved|rewritten|blocked) with risk_level, reason, architect_notes, rewrite_summary
- format_plan_comment(plan, architect_section=None) — inserts section before <details>
- update_plan_comment_with_architect_section — finds plan comment, injects/replaces booty-architect block
- post_architect_blocked_comment refactored to update same comment; reason param; fallback to new if none found

## Task Commits

1. **Task 1: format_architect_section and format_plan_comment update** - `118f2ca` (feat)
2. **Task 2 & 3: update_plan_comment_with_architect_section, post_architect_blocked_comment refactor** - `36939ba` (feat)

## Files Created/Modified

- `src/booty/architect/output.py` - format_architect_section
- `src/booty/planner/output.py` - format_plan_comment(architect_section param)
- `src/booty/github/comments.py` - update_plan_comment_with_architect_section, post_architect_blocked_comment(reason)

## Decisions Made

None - followed plan as specified

## Deviations from Plan

None - plan executed exactly as written

## Issues Encountered

None

## Next Phase Readiness

- format_architect_section, format_plan_comment, update_plan_comment_with_architect_section ready for main.py wiring
- post_architect_blocked_comment accepts reason param for 34-03 block flow

---
*Phase: 34-output-failure-handling*
*Completed: 2026-02-17*
