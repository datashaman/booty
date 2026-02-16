---
phase: 21-permission-drift-governor-integration
plan: 01
subsystem: security
tags: [pathspec, git, override, ESCALATE]

requires:
  - phase: 18
    provides: Security runner, booty/security check, pull_request trigger
provides:
  - permission_drift module (get_changed_paths, sensitive_paths_touched)
  - override persistence (persist_override → security_overrides.json)
  - runner integration (ESCALATE when sensitive paths touched)
affects: [21-02 Governor override integration]

tech-stack:
  added: []
  patterns: [PathSpec gitwildmatch, atomic write + fcntl LOCK_EX]

key-files:
  created: [src/booty/security/permission_drift.py, src/booty/security/override.py]
  modified: [src/booty/security/runner.py]

key-decisions:
  - "Use PathSpec.from_lines('gitwildmatch', ...) for sensitive path matching"
  - "Override stored in state_dir/security_overrides.json, same as Governor"

patterns-established:
  - "ESCALATE = conclusion success, title 'Security escalated — …', override persisted"
  - "Renames: both old and new path matched against sensitive_paths"

duration: 15min
completed: 2026-02-16
---

# Phase 21 Plan 01: Permission Drift Detection — Summary

**Sensitive path touch → ESCALATE (success + title), override persisted for Governor; PR not blocked**

## Performance

- **Duration:** ~15 min
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- permission_drift module: get_changed_paths (git diff --name-status -z), sensitive_paths_touched (PathSpec), _title_for_paths (category mapping)
- override module: persist_override to security_overrides.json with risk_override=HIGH, reason=permission_surface_change
- runner integration: after audit passes, check permission drift; if touched → edit_check_run success + title, persist_override, return

## Task Commits

1. **Task 1: permission_drift module** — `ed53ed9` (feat)
2. **Task 2: override persistence** — `d4a568b` (feat)
3. **Task 3: runner integration** — `4edfb18` (feat)

## Files Created/Modified

- `src/booty/security/permission_drift.py` — get_changed_paths, sensitive_paths_touched, _title_for_paths
- `src/booty/security/override.py` — persist_override with atomic write + LOCK_EX
- `src/booty/security/runner.py` — Permission drift check after audit, ESCALATE flow
- `tests/test_security_permission_drift.py` — Unit tests for drift detection
- `tests/test_security_override.py` — Unit tests for override persistence

## Decisions Made

None — followed plan as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

Override persistence ready for Governor (21-02) to consume via get_security_override.

---
*Phase: 21-permission-drift-governor-integration*
*Completed: 2026-02-16*
