---
phase: 10-import-compile-detection
plan: 02
subsystem: testing
tags: [ast, py_compile, importlib, verifier, annotations]

provides:
  - verifier/imports.py with compile_sweep, validate_imports, parse_setup_stderr, prepare_check_annotations
  - Annotation dict format for GitHub Checks API

key-files:
  created: [src/booty/verifier/imports.py]

key-decisions:
  - "compile_sweep uses py_compile.compile with doraise=True; PyCompileError exc_value for lineno"
  - "validate_imports runs subprocess in workspace; injects script via python -c"
  - "prepare_check_annotations dedupes first, then caps at 50"

completed: 2026-02-15
---

# Phase 10 Plan 02 Summary

**verifier/imports.py with compile sweep (py_compile), import validation (subprocess), and annotation formatting for checks output.**

## Accomplishments

- `compile_sweep(file_paths, workspace_root)` — py_compile per .py file, returns annotation dicts for SyntaxError
- `validate_imports(file_paths, workspace_path, timeout)` — async subprocess in workspace, ast.parse + importlib.import_module
- `parse_setup_stderr(stderr, workspace_path)` — regex for File "path", line N and path:N:
- `prepare_check_annotations(annotations, cap=50)` — dedupe by (path, start_line, message), cap at 50

## Task Commits

1. **Task 1: compile_sweep** — py_compile, PyCompileError handling
2. **Task 2: validate_imports** — subprocess in workspace, JSON output
3. **Task 3: parse_setup_stderr, prepare_check_annotations** — regex parsing, dedup+cap

## Files Created

- `src/booty/verifier/imports.py` — full module

## Deviations from Plan

None — plan executed as specified.

---
*Phase: 10-import-compile-detection*
*Completed: 2026-02-15*
