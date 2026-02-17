---
phase: 47-operator-visibility
plan: 01
subsystem: infra
tags: logging, router, skip_reasons, observability

provides:
  - Structured event_skip logs with five-bucket vocabulary (OPS-01, OPS-02)
  - INFO for operator-actionable skips; DEBUG for high-volume
  - dedup_hit logging for verifier, reviewer, security, planner, architect

key-files:
  created: src/booty/router/skip_reasons.py
  modified: src/booty/router/router.py

key-decisions:
  - "Used queue workers for record_agent_completed (verifier, security, reviewer) instead of runner — guarantees recording on all exit paths"
---

# Phase 47: Operator Visibility — Plan 01 Summary

**Structured skip logs with five-bucket vocabulary, INFO/DEBUG split, and dedup_hit coverage for all PR and issue agents**

## Accomplishments

- Created `skip_reasons.py` with `REASON_TO_BUCKET` mapping, `INFO_BUCKETS`, and `_log_event_skip(agent, repo, event_type, reason, _reason_raw)`
- Replaced all `logger.info("event_skip", ...)` in router with `_log_event_skip` calls
- Added dedup_hit logging for verifier, reviewer, security when `is_duplicate` blocks enqueue
- Added dedup_hit for planner and architect when `*_is_duplicate` returns
- Replaced `verifier_already_processed` with `_log_event_skip(agent="verifier", reason="dedup_hit")`
- Replaced `builder_blocked_no_plan` with `_log_event_skip`
- Added `_log_event_skip` for `no_job_queue`, `self_modification_disabled`

## Files Created/Modified

- `src/booty/router/skip_reasons.py` — New: reason-to-bucket mapping, INFO/DEBUG selection, _log_event_skip
- `src/booty/router/router.py` — All skip paths use _log_event_skip

## Deviations from Plan

None — plan executed as specified.

---
*Phase: 47-operator-visibility*
*Completed: 2026-02-17*
