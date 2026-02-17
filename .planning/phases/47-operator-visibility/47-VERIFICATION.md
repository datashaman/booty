# Phase 47: Operator Visibility — Verification

**Verified:** 2026-02-17
**Status:** passed

## Must-Haves Check

### OPS-01: Structured skip logs with agent, repo, event_type, decision=skip, reason

**Verified:** Yes
- `skip_reasons._log_event_skip` emits `decision="skip"` and five-bucket `reason`
- All router skip paths use `_log_event_skip` (20+ call sites in router.py)

### OPS-02: Five-bucket vocabulary (disabled, not_agent_pr, missing_config, dedup_hit, normalize_failed)

**Verified:** Yes
- `skip_reasons.py`: REASON_TO_BUCKET maps all granular reasons; INFO_BUCKETS = disabled, missing_config, normalize_failed
- INFO for operator-actionable; DEBUG for high-volume (not_agent_pr, dedup_hit)

### OPS-03: booty status shows enabled, last_run_completed_at, queue_depth; Builder and Reviewer

**Verified:** Yes
- `booty status` outputs per-agent: enabled, last_run_completed_at, queue_depth
- Builder and Reviewer included
- `booty status --json` returns structured object with all fields
- operator/last_run.py: record_agent_completed, get_last_run
- Six agents wired: verifier, security, reviewer, planner, architect, builder

### OPS-04: promotion_waiting_reviewer in Verifier; documented

**Verified:** Yes
- `grep promotion_waiting_reviewer src/booty/verifier/runner.py` — present
- `docs/capabilities-summary.md` references OPS-04 and promotion_waiting_reviewer

## Summary

| Must-Have | Status |
|-----------|--------|
| OPS-01 | ✓ |
| OPS-02 | ✓ |
| OPS-03 | ✓ |
| OPS-04 | ✓ |

**Score:** 4/4

---
*Phase: 47-operator-visibility*
