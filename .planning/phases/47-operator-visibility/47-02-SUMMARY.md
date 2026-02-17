---
phase: 47-operator-visibility
plan: 02
subsystem: infra
tags: cli, operator, last_run, status, observability

provides:
  - booty status shows enabled, last_run_completed_at, queue_depth per agent
  - Builder and Reviewer in status output
  - last_run.json store with record_agent_completed / get_last_run

key-files:
  created: src/booty/operator/__init__.py, src/booty/operator/last_run.py
  modified: src/booty/cli.py, src/booty/verifier/queue.py, src/booty/security/queue.py, src/booty/reviewer/queue.py, src/booty/planner/worker.py, src/booty/architect/review.py, src/booty/main.py

key-decisions:
  - "Wired record_agent_completed in queue workers (verifier, security, reviewer) — ensures recording on all exit paths including exceptions"
  - "queue_depth: N/A — status runs standalone without app_state"
---

# Phase 47: Operator Visibility — Plan 02 Summary

**booty status CLI extended with last_run_completed_at, queue_depth, Builder and Reviewer; operator last_run store with six agents wired**

## Accomplishments

- Created `operator/last_run.py` with `record_agent_completed(agent)` and `get_last_run(agent)`, JSON store at `state_dir/operator/last_run.json`
- Wired verifier, security, reviewer queues to call `record_agent_completed` in worker finally blocks
- Wired planner worker to call `record_agent_completed("planner")` after plan stored
- Wired architect: `architect/review.py` (CLI path) and main.py architect worker loop
- Wired builder: `process_job` try/finally with `record_agent_completed("builder")`
- Extended `booty status` with Builder and Reviewer, last_run_completed_at, queue_depth (N/A) for all eight agents
- JSON output includes per-agent enabled, last_run_completed_at, queue_depth

## Files Created/Modified

- `src/booty/operator/__init__.py`, `last_run.py` — New
- `src/booty/cli.py` — Extended status with new fields and agents
- `src/booty/verifier/queue.py`, `security/queue.py`, `reviewer/queue.py` — record_agent_completed in finally
- `src/booty/planner/worker.py` — record_agent_completed after save_plan
- `src/booty/architect/review.py` — record_agent_completed after process_architect_input
- `src/booty/main.py` — record_agent_completed for architect worker and builder (process_job)

## Deviations from Plan

- Used queue workers instead of runners for verifier/security/reviewer — same outcome, cleaner (single recording point per job)

---
*Phase: 47-operator-visibility*
*Completed: 2026-02-17*
