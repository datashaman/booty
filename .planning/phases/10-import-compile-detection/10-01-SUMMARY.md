---
phase: 10-import-compile-detection
plan: 01
subsystem: testing
tags: [pydantic, booty-config, install-command]

provides:
  - BootyConfigV1.install_command field (optional, default None)
  - Schema v1 accepts install_command for Verifier import validation

key-files:
  modified: [src/booty/test_runner/config.py]

key-decisions:
  - "install_command placed after setup_command for logical 'prepare env' grouping"

completed: 2026-02-15
---

# Phase 10 Plan 01 Summary

**BootyConfigV1 schema extended with install_command for Verifier dependency installation before import validation.**

## Accomplishments

- Added `install_command: str | None` to BootyConfigV1 (after setup_command)
- Backward compatible: omit or null yields None
- Enables Verifier to run `pip install -r requirements.txt` before import sweep

## Task Commits

1. **Task 1: Add install_command to BootyConfigV1** — config.py modified

## Files Modified

- `src/booty/test_runner/config.py` — install_command Field added

## Deviations from Plan

None — plan executed as specified.

---
*Phase: 10-import-compile-detection*
*Completed: 2026-02-15*
