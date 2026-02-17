---
phase: 44-planner-architect-builder-wiring
plan: 01
subsystem: pipeline
tags: asyncio, architect, dedup, worker

requires:
  - phase: 43
    provides: Dedup keys alignment (repo_full_name)
provides:
  - ArchitectJob dataclass and architect_queue for webhook-triggered Architect
  - architect_is_duplicate(repo, plan_hash) for dedup
  - _architect_worker_loop consuming ArchitectJob, running validation, enqueueing Builder on approval
affects: Phase 44-03 (router will call architect_enqueue)

tech-stack:
  added: []
  patterns: Architect standalone worker mirroring Planner worker pattern

key-files:
  created: src/booty/architect/jobs.py
  modified: src/booty/main.py

key-decisions:
  - Architect dedup by (repo_full_name, plan_hash) per Phase 43
  - architect_processed capped at 1000, evict oldest

duration: 15min
completed: 2026-02-17
---

# Phase 44 Plan 01: Architect Standalone Enqueue Summary

**ArchitectJob, architect_queue, architect worker loop — webhook-triggered Architect path for issues with existing plan but unreviewed**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `src/booty/architect/jobs.py`: ArchitectJob dataclass with plan_hash; architect_queue; architect_processed with cap 1000; architect_is_duplicate, architect_mark_processed, architect_enqueue
- `main.py`: _architect_worker_loop consumes ArchitectJob, loads plan via get_plan_for_issue, runs process_architect_input, on approval saves artifact and enqueues Builder, on block posts comment and label, cancelled on app shutdown

## Task Commits

1. **Task 1: Create architect/jobs.py** - `1def7db` (feat)
2. **Task 2: Add Architect worker loop in main.py** - `b7c3ac7` (feat)

## Files Created/Modified

- `src/booty/architect/jobs.py` - ArchitectJob, architect_queue, architect_processed, architect_is_duplicate, architect_mark_processed, architect_enqueue
- `src/booty/main.py` - _architect_worker_loop, architect_queue in app.state, architect_worker_task lifecycle

## Decisions Made

- Used f"{repo_full_name}:{plan_hash}" as architect_processed key for simplicity
- Architect worker gets architect_config from load_booty_config_for_repo; defaults to ArchitectConfig() when no booty_config

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

WIRE-02 enqueue path exists (router will call architect_enqueue in Plan 03). Architect dedup by (repo, plan_hash). Architect worker mirrors Planner→Architect inline flow without Planner.

---
*Phase: 44-planner-architect-builder-wiring*
*Completed: 2026-02-17*
