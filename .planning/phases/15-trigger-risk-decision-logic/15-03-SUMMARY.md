---
phase: 15-trigger-risk-decision-logic
plan: 03
subsystem: release-governor
tags: webhook, workflow_run, handler, PyGithub

# Dependency graph
requires:
  - phase: 15-01
    provides: compute_risk_class
  - phase: 15-02
    provides: compute_decision
provides:
  - workflow_run webhook route
  - handle_workflow_run full pipeline
  - Idempotency via delivery cache
affects: phase-16

key-files:
  created: [tests/test_release_governor_handler.py]
  modified: [src/booty/webhooks.py, src/booty/release_governor/handler.py, src/booty/test_runner/config.py]

key-decisions:
  - "Config loaded from repo .booty.yml via GitHub API (not local file)"
  - "Approval: env only for Phase 15; label/comment TODO for Phase 16"

patterns-established: []

# Metrics
duration: 15min
completed: 2026-02-16
---

# Phase 15 Plan 03: workflow_run Webhook & Handler Summary

**workflow_run webhook route and handle_workflow_run full pipeline (GOV-01, GOV-02, GOV-03)**

## Performance

- **Duration:** ~15 min
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments

- verification_workflow_name in ReleaseGovernorConfig ("Verify main")
- workflow_run branch in github webhook: filter by verification success on main
- Config loaded from repo .booty.yml via PyGithub
- Idempotency: has_delivery_id / record_delivery_id
- handle_workflow_run: risk from diff, decision, returns Decision
- Env approval (RELEASE_GOVERNOR_APPROVED); label/comment TODO Phase 16
- 2 handler integration tests

## Task Commits

1. **Task 1: Add verification_workflow_name** - `7b5171d` (feat)
2. **Task 2: Add workflow_run branch to webhooks** - `9e33a3f` (feat)
3. **Task 3: Implement handle_workflow_run** - `0f2bd44` (feat)
4. **Task 4: Add handler tests** - `7e6e1fe` (test)

**Plan metadata:** (pending)

## Files Created/Modified

- `src/booty/test_runner/config.py` - verification_workflow_name
- `src/booty/webhooks.py` - workflow_run handler branch
- `src/booty/release_governor/handler.py` - handle_workflow_run implementation
- `tests/test_release_governor_handler.py` - 2 integration tests

## Decisions Made

- Config fetched from target repo .booty.yml (not local) — Governor is multi-tenant
- Env approval only for Phase 15; label/comment require PR lookup, deferred to Phase 16

## Deviations from Plan

None - plan executed as specified.

## Issues Encountered

None.

## Next Phase Readiness

Ready for Phase 16 (Deploy Integration & Operator UX).

---
*Phase: 15-trigger-risk-decision-logic*
*Completed: 2026-02-16*
