---
phase: 21-permission-drift-governor-integration
plan: 02
subsystem: release_governor
tags: [override, risk, security_overrides]

requires:
  - phase: 21-01
    provides: persist_override → security_overrides.json
provides:
  - override read module (get_security_override, get_security_override_with_poll)
  - handler integration (override before compute_risk_class)
  - prune expired entries (14 days) on read
affects: []

tech-stack:
  added: []
  patterns: [LOCK_SH read, prune on read, poll for race]

key-files:
  created: [src/booty/release_governor/override.py]
  modified: [src/booty/release_governor/handler.py]

key-decisions:
  - "RELEASE_GOVERNOR_OVERRIDE_POLL_SEC env for poll timeout (default 120)"
  - "max_wait_sec=0 → check once, no poll"

patterns-established:
  - "Override present → risk_class HIGH, skip compute_risk_class"
  - "Poll handles race when Governor runs before Security"

duration: 12min
completed: 2026-02-16
---

# Phase 21 Plan 02: Governor Override Integration — Summary

**Governor consumes Security override; when present uses risk_class=HIGH for deploy gating**

## Performance

- **Duration:** ~12 min
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- override module: get_security_override (read + prune 14-day expired), get_security_override_with_poll (poll up to 2 min)
- handler integration: handle_workflow_run and simulate_decision_for_cli check override before compute_risk_class
- Override present → risk_class HIGH; absent → normal path-based risk

## Task Commits

1. **Task 1: override read module** — `8ae798d` (feat)
2. **Task 2: handler integration** — `7537a72` (feat)
3. **Task 3: override tests** — `35ec0e9` (test)

## Files Created/Modified

- `src/booty/release_governor/override.py` — get_security_override, get_security_override_with_poll, prune
- `src/booty/release_governor/handler.py` — Override check before compute_risk_class
- `tests/test_release_governor_override.py` — Read, prune, poll, handler integration tests

## Decisions Made

- Added RELEASE_GOVERNOR_OVERRIDE_POLL_SEC env for poll timeout (default 120s)
- Handler tests patch get_security_override_with_poll to avoid 2-min wait when no override

## Deviations from Plan

None significant — plan executed as specified.

## Issues Encountered

- Handler tests would hang 2 min without override; patched get_security_override_with_poll in those tests

## Next Phase Readiness

Phase 21 complete. Permission drift + Governor integration delivered.

---
*Phase: 21-permission-drift-governor-integration*
*Completed: 2026-02-16*
