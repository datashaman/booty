---
phase: 38-agent-pr-detection-event-wiring
plan: 03
subsystem: reviewer
tags: runner, lifespan, check_run, cancel
requires:
  - phase: 38-01
    provides: ReviewerJob, ReviewerQueue
provides:
  - process_reviewer_job runner stub with check lifecycle
  - reviewer_queue started in lifespan when verifier_enabled
  - Worker cancel checks and queue _cancel_events cleanup
affects: 39
tech-stack:
  added: []
  patterns: Load config before creating check; no-op when disabled
key-files:
  created: src/booty/reviewer/runner.py
  modified: src/booty/main.py, src/booty/config.py
key-decisions:
  - "Worker loads .booty.yml first; no check when get_reviewer_config returns None"
  - "Check titles: Booty Reviewer (queued/in progress), Reviewer approved (stub success)"
  - "conclusion=cancelled when worker exits due to cancel_event"
patterns-established:
  - "Reviewer queue created when verifier_enabled (same App credentials)"
duration: 5min
completed: 2026-02-17
---

# Phase 38: Agent PR Detection + Event Wiring — Plan 03 Summary

**Reviewer runner stub and reviewer_queue lifespan wiring**

## Performance

- **Duration:** ~5 min
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- process_reviewer_job: loads config first, no check when disabled; creates check with titles Booty Reviewer / Reviewer approved
- Cancel checks at phase boundaries; edit_check_run(conclusion="cancelled") on exit
- reviewer_queue in lifespan when verifier_enabled; REVIEWER_WORKER_COUNT in config
- Queue worker clears _cancel_events on job completion (try/finally)

## Task Commits

1. **Task 1: process_reviewer_job** — `ff6f450` (feat(38-03))
2. **Task 2+3: lifespan and cancel** — `54e8105` (feat(38-03))

## Files Created/Modified

- `src/booty/reviewer/runner.py` — process_reviewer_job stub
- `src/booty/main.py` — reviewer_queue, _process_reviewer_job, lifespan
- `src/booty/config.py` — REVIEWER_WORKER_COUNT

## Deviations from Plan

Load config before creating check (CONTEXT: "no check when disabled" → worker must not create check if disabled).

## Issues Encountered

None

---
*Phase: 38-agent-pr-detection-event-wiring*
*Completed: 2026-02-17*
