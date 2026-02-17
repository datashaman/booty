---
phase: 42-event-router
plan: 02
subsystem: router
tags: [routing, config, precedence, should_run]

requires:
  - phase: 42-01
    provides: [events, normalizer]
provides:
  - should_run(agent, repo, context) single decision point
  - enabled(agent) with config+env precedence
  - RoutingContext TypedDict
  - BOOTY_DISABLED global kill switch
affects: [42-03]

tech-stack:
  added: []
  patterns: [env > file > default precedence, two-layer enabled vs should_run]

key-files:
  created: [src/booty/router/should_run.py]
  modified: [src/booty/router/__init__.py]

key-decisions:
  - BOOTY_DISABLED for global kill switch
  - Reviewer gating via is_agent_pr in context
  - builder uses planner_enabled as proxy

patterns-established:
  - "enabled(agent) = layer 1; should_run(agent, ctx) = layer 2"

duration: 5min
completed: 2026-02-17
---

# Phase 42 Plan 02: should_run Summary

**Single should_run(agent, repo, context) decision point with config+env precedence. ROUTE-05.**

## Performance

- **Duration:** 5 min
- **Completed:** 2026-02-17
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- should_run.py with enabled(), should_run(), RoutingContext
- All agents: planner, verifier, security, reviewer, builder, architect, governor
- BOOTY_DISABLED global kill switch
- Reviewer gating: is_agent_pr required
- Planner gating: has_trigger_label required
- router package exports enabled, should_run, RoutingContext

## Task Commits

1. **Task 1: Create should_run module** - `c332865` (feat)
2. **Task 2+3: Wire Reviewer, Export** - `9aec2d7` (feat)

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

- should_run ready for router (42-03) to wire all enqueue paths

---
*Phase: 42-event-router*
*Completed: 2026-02-17*
