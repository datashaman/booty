---
phase: 44-planner-architect-builder-wiring
plan: 02
subsystem: pipeline
tags: architect, config, builder_compat, migration

requires:
  - phase: 44-01
    provides: ArchitectConfig usage
provides:
  - ArchitectConfig.builder_compat (default True) — migration aid for Architect-only enforcement
  - get_plan_for_builder(..., builder_compat=False) returns (None, False) when no Architect artifact
  - ARCHITECT_BUILDER_COMPAT env override
affects: Phase 44-03 (router uses builder_compat)

tech-stack:
  added: []
  patterns: Config precedence env overrides file over default

key-files:
  created: []
  modified: src/booty/architect/config.py, src/booty/architect/artifact.py, src/booty/main.py, src/booty/router/router.py

key-decisions:
  - builder_compat defaults True (safe migration)
  - architect disabled -> builder_compat True (Builder uses Planner plan directly)

duration: 10min
completed: 2026-02-17
---

# Phase 44 Plan 02: Compat Flag Summary

**ArchitectConfig.builder_compat and get_plan_for_builder — Builder Planner fallback only when compat enabled; WIRE-04**

## Performance

- **Duration:** ~10 min
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- ArchitectConfig.builder_compat = True default; ARCHITECT_BUILDER_COMPAT env (1/true/yes, 0/false/no)
- get_plan_for_builder(..., builder_compat=False) returns (None, False) when no Architect artifact — no Planner fallback
- main.py process_job and router _route_issues both pass builder_compat from architect_config (True when architect disabled)

## Task Commits

1. **Task 1: Add builder_compat to ArchitectConfig** - `84d0906` (feat)
2. **Task 2: get_plan_for_builder respects compat** - `5791ed1` (feat)
3. **Task 3: Update get_plan_for_builder callers** - `afbb19c` (feat)

## Files Created/Modified

- `src/booty/architect/config.py` - builder_compat field, ARCHITECT_BUILDER_COMPAT in apply_architect_env_overrides
- `src/booty/architect/artifact.py` - get_plan_for_builder builder_compat param and logic
- `src/booty/main.py` - load booty_config, get architect_config, pass builder_compat to get_plan_for_builder
- `src/booty/router/router.py` - builder_compat from architect_config, pass to get_plan_for_builder

## Decisions Made

- architect disabled -> builder_compat=True (Architect skipped implies compat; Builder uses Planner plan directly)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

WIRE-04 complete. Builder Planner fallback only when compat enabled. Router and process_job pass builder_compat from config.

---
*Phase: 44-planner-architect-builder-wiring*
*Completed: 2026-02-17*
