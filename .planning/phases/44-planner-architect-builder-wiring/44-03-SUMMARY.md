---
phase: 44-planner-architect-builder-wiring
plan: 03
subsystem: pipeline
tags: router, plan-state-first, architect, planner, builder

requires:
  - phase: 44-01
    provides: architect_enqueue, ArchitectJob, architect_queue
  - phase: 44-02
    provides: get_plan_for_builder with builder_compat
provides:
  - Plan-state-first _route_issues: resolve plan before any enqueue
  - Architect-approved plan -> Builder only (WIRE-01)
  - Unreviewed plan -> Architect enqueue (WIRE-02)
  - No plan -> Planner enqueue (WIRE-03)
affects: Phase 44-04 (docs/routing.md documents this)

tech-stack:
  added: []
  patterns: Plan-state-first routing (no Planner-first branch)

key-files:
  created: []
  modified: src/booty/router/router.py

key-decisions:
  - Removed Planner-first branch; plan state drives routing

duration: 20min
completed: 2026-02-17
---

# Phase 44 Plan 03: Router Plan-State-First Summary

**Plan-state-first _route_issues — Architect-approved -> Builder; unreviewed -> Architect; no plan -> Planner; WIRE-01, WIRE-02, WIRE-03**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- _route_issues rewritten: resolve plan via get_plan_for_builder before any enqueue decision
- architect_enabled + plan + not unreviewed -> Builder
- architect_enabled + plan + unreviewed -> Architect (architect_enqueue, architect_plan_hash for dedup)
- architect_enabled + no plan -> Planner (or builder_blocked when Planner disabled)
- architect disabled: plan -> Builder; no plan -> Planner

## Task Commits

1. **Task 1: Replace Planner-first with plan-state-first** - `724185b` (feat)
2. **Task 2: Use architect_plan_hash for Architect dedup** - (in same commit)

## Files Created/Modified

- `src/booty/router/router.py` - plan-state-first _route_issues; Architect enqueue path with architect_plan_hash; background_tasks passed to _route_issues

## Decisions Made

- _do_builder_enqueue helper returns (status_dict, None) for early-exit or (None, (job_id, job)) for enqueue
- Architect job_id format: architect-{issue}-{delivery_id}

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

WIRE-01, WIRE-02, WIRE-03 complete. Router uses plan-state-first. Plan 44-04 will document routing logic in docs/routing.md.

---
*Phase: 44-planner-architect-builder-wiring*
*Completed: 2026-02-17*
