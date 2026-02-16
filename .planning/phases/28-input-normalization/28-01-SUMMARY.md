---
phase: 28-input-normalization
plan: 01
subsystem: planner
tags: pydantic, github, sentry, normalization

requires: []
provides:
  - PlannerInput Pydantic model
  - normalize_github_issue, normalize_cli_text, normalize_from_job
  - derive_source_type, incident detection (label + heuristics)
  - _extract_incident_fields for Location/Sentry
affects: [28-02, 28-03, 29]

tech-stack:
  added: []
  patterns: [source-specific normalizers, label-primary heuristics-fallback]

key-files:
  created: [src/booty/planner/input.py, tests/test_planner_input.py]
  modified: []

key-decisions:
  - "2+ markers (Severity + Sentry) for incident heuristics per RESEARCH pitfall"
  - "First line = goal for CLI text; body trimmed to 8k chars"

patterns-established:
  - "PlannerInput: goal, body, labels, source_type, metadata, incident_fields, repo_context"
  - "normalize_* returns PlannerInput; repo_context optional passthrough"

duration: ~10min
completed: 2026-02-16
---

# Phase 28: Input Normalization Plan 01 Summary

**PlannerInput Pydantic model with GitHub issue and CLI text normalizers, Sentry incident detection via label + body heuristics**

## Performance

- **Duration:** ~10 min
- **Tasks:** 3
- **Files modified:** 2 (created)

## Accomplishments

- PlannerInput model with goal, body, labels, source_type, metadata, incident_fields, repo_context
- Incident detection: agent:incident label primary; **Severity:** + **Sentry:** heuristics fallback (2+ markers per pitfall)
- _extract_incident_fields for Location and Sentry URL
- normalize_github_issue, normalize_cli_text, normalize_from_job
- 19 tests covering validation, derivation, extraction, normalizers

## Task Commits

1. **Task 1+2: PlannerInput model, normalizers** - `fdd85f1` (feat)
2. **Task 3: Tests** - `d2708b8` (test)

**Plan metadata:** pending (docs commit after SUMMARY)

## Files Created/Modified

- `src/booty/planner/input.py` - PlannerInput, normalizers, incident detection
- `tests/test_planner_input.py` - 19 tests

## Deviations from Plan

None - plan executed exactly as written

## Issues Encountered

None

## Next Phase Readiness

- 28-02 can add get_repo_context; normalizers already accept repo_context
- 28-03 can wire worker/CLI to normalizers

---
*Phase: 28-input-normalization*
*Completed: 2026-02-16*
