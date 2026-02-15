---
phase: 10-import-compile-detection
plan: 03
subsystem: testing
tags: [verifier, runner, checks, annotations]

provides:
  - Full Phase 10 pipeline: setup → install → import/compile → tests
  - edit_check_run annotations support
  - Agent PR install_command requirement
  - Check output with annotations on import/compile failure

key-files:
  modified: [src/booty/verifier/runner.py, src/booty/github/checks.py]

key-decisions:
  - "Execution order: setup_command → install_command → import/compile sweep → test_command"
  - "Agent PR with BootyConfigV1: install_command required, fail fast with clear message"
  - "validate_imports only when install_command present; compile_sweep always for .py files"

completed: 2026-02-15
---

# Phase 10 Plan 03 Summary

**Full Verifier pipeline with setup_command, install_command, import/compile sweep, and annotated check output on failures.**

## Accomplishments

- edit_check_run docstring documents annotations (path, start_line, end_line, annotation_level, message, title)
- Runner: agent PR + BootyConfigV1 without install_command → fail "Config required for agent PRs: install_command."
- Runner: setup_command runs first, install_command second; failures produce annotated output
- Runner: get_pr_diff_stats → py_files → compile_sweep + validate_imports (when install present)
- Failure titles: "Import errors" | "Compile errors" | "Multiple failure classes"
- Annotations capped at 50 via prepare_check_annotations

## Task Commits

1. **Task 1: edit_check_run annotations** — docstring, output passes through
2. **Task 2: Execution order + agent install_command check** — setup/install before tests
3. **Task 3: Import/compile sweep wiring** — compile_sweep, validate_imports, failure reporting

## Files Modified

- `src/booty/github/checks.py` — edit_check_run docstring
- `src/booty/verifier/runner.py` — full Phase 10 pipeline

## Deviations from Plan

None — plan executed as specified.

---
*Phase: 10-import-compile-detection*
*Completed: 2026-02-15*
