---
phase: 35-idempotency
plan: 03
subsystem: architect
tags: cache, idempotency, main, planner-worker

requires:
  - phase: 35-01
    provides: architect_plan_hash, find_cached_architect_result, save_architect_result
  - phase: 35-02
    provides: get_plan_comment_body, update_plan_comment_with_architect_section_if_changed
provides: Architect idempotency flow in _planner_worker_loop

key-files:
  created: []
  modified: src/booty/main.py

key-decisions:
  - "Cache check before process_architect_input; short-circuit on hit"
  - "No add_architect_review_label on blocked cache hit (label already from first block)"
  - "Blocked fallback: get_plan_comment_body → update_if_changed else post_architect_blocked_comment"

duration: 8min
completed: 2026-02-17
---

# Phase 35 Plan 03: Main Flow Integration Summary

**Architect cache integrated: cache check before validation, save on miss, diff-before-update for comments**

## Accomplishments

- Cache check before process_architect_input using architect_plan_hash, find_cached_architect_result
- Cache hit (approved): build ArchitectPlan from cached.plan, update_plan_comment_with_architect_section_if_changed, enqueue Builder
- Cache hit (blocked): format section, update only if changed; no re-validation, no label re-add
- Cache miss: process_architect_input, save_architect_result (approved/blocked), update_if_changed or post_architect_blocked_comment
- ARCH-23, ARCH-24, ARCH-25 satisfied

## Task Commits

1. **Task 1-3: Integrate Architect cache** - feat(35-03)

## Files Created/Modified

- `src/booty/main.py` - cache check, save, diff-before-update

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

Phase 35 Idempotency complete. Ready for Phase 36 Builder Handoff & CLI.
