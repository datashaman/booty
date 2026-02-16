---
phase: 15-trigger-risk-decision-logic
plan: 01
subsystem: release-governor
tags: pathspec, risk, PyGithub

# Dependency graph
requires: []
provides:
  - compute_risk_class from diff vs production_sha
  - medium_risk_paths config and env override
  - Risk scoring unit tests
affects: phase-15-plan-02, phase-15-plan-03

key-files:
  created: [src/booty/release_governor/risk.py, tests/test_release_governor_risk.py]
  modified: [src/booty/test_runner/config.py, src/booty/release_governor/__init__.py]

key-decisions: []
patterns-established:
  - "PathSpec gitwildmatch for risk path matching (consistent with verifier/limits)"

# Metrics
duration: 8min
completed: 2026-02-16
---

# Phase 15 Plan 01: Risk Scoring Summary

**Risk class (LOW/MEDIUM/HIGH) computed from diff vs production_sha using pathspec matching**

## Performance

- **Duration:** ~8 min
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- ReleaseGovernorConfig extended with medium_risk_paths (dependency manifests)
- RELEASE_GOVERNOR_MEDIUM_RISK_PATHS env override (comma-separated)
- risk.py with compute_risk_class using PathSpec for high/medium paths
- Empty diff → LOW; multi-category match takes highest risk
- 6 unit tests covering all risk cases

## Task Commits

1. **Task 1: Add medium_risk_paths and extend config** - `62057c3` (feat)
2. **Task 2: Create risk.py with compute_risk_class** - `2ff15cd` (feat)
3. **Task 3: Add risk scoring tests** - `fff6f0d` (test)

**Plan metadata:** (pending)

## Files Created/Modified

- `src/booty/test_runner/config.py` - medium_risk_paths, env override
- `src/booty/release_governor/risk.py` - compute_risk_class
- `src/booty/release_governor/__init__.py` - export compute_risk_class
- `tests/test_release_governor_risk.py` - 6 unit tests

## Decisions Made

None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Ready for 15-02-PLAN.md (decision engine).

---
*Phase: 15-trigger-risk-decision-logic*
*Completed: 2026-02-16*
