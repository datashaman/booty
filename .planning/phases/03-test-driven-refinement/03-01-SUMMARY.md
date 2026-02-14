---
phase: 03-test-driven-refinement
plan: 01
subsystem: testing
tags: [pyyaml, tenacity, asyncio, subprocess, pydantic]

# Dependency graph
requires:
  - phase: 02-llm-code-generation
    provides: FileChange models and code generation pipeline
provides:
  - .booty.yml config loading with Pydantic validation
  - Async subprocess test execution with timeout control
  - Test output parsing for error extraction and file identification
affects: [03-test-driven-refinement, code-refinement]

# Tech tracking
tech-stack:
  added: [pyyaml, tenacity]
  patterns: [async subprocess with timeout, YAML config validation, traceback parsing]

key-files:
  created:
    - src/booty/test_runner/__init__.py
    - src/booty/test_runner/config.py
    - src/booty/test_runner/executor.py
    - src/booty/test_runner/parser.py
  modified:
    - pyproject.toml

key-decisions:
  - "PyYAML for config parsing with Pydantic validation"
  - "asyncio.wait_for with proc.kill() + proc.wait() to prevent zombie processes"
  - "Exclude test files from error file extraction to focus on source code"
  - "errors='replace' for UTF-8 decoding to handle non-standard output"

patterns-established:
  - "BootyConfig Pydantic model with field validators for test configuration"
  - "TestResult dataclass for structured subprocess output capture"
  - "Traceback parsing with heuristic filtering for error context"

# Metrics
duration: 2min
completed: 2026-02-14
---

# Phase 03 Plan 01: Test Runner Module Summary

**Async subprocess test execution with .booty.yml config validation, timeout control, and intelligent error parsing for test-driven refinement**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-14T14:10:29Z
- **Completed:** 2026-02-14T14:12:55Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created test_runner module with config, executor, and parser components
- Implemented BootyConfig Pydantic model for .booty.yml validation
- Implemented async subprocess execution with timeout and zombie process prevention
- Implemented intelligent error parsing to extract relevant context and identify failing files

## Task Commits

Each task was committed atomically:

1. **Task 1: Add dependencies and create test_runner config module** - `3775f18` (chore)
2. **Task 2: Create test executor and output parser** - `bac4915` (feat)

## Files Created/Modified
- `pyproject.toml` - Added pyyaml and tenacity dependencies
- `src/booty/test_runner/__init__.py` - Module initialization
- `src/booty/test_runner/config.py` - BootyConfig model and load_booty_config function
- `src/booty/test_runner/executor.py` - TestResult dataclass and execute_tests async function
- `src/booty/test_runner/parser.py` - extract_error_summary and extract_files_from_output functions

## Decisions Made

**PyYAML for config parsing with Pydantic validation**
- Using yaml.safe_load() for security (prevents arbitrary code execution)
- Pydantic BaseModel provides type-safe validation with clear error messages
- Follows existing pattern from Phase 1 (pydantic-settings) and Phase 2 (llm.models)

**Timeout handling with zombie process prevention**
- asyncio.wait_for() wraps proc.communicate() for timeout control
- Critical: proc.kill() followed by await proc.wait() to reap zombie processes
- Follows 03-RESEARCH.md Pattern 1 exactly

**Error parsing excludes test files**
- extract_files_from_output filters out files with 'test' in path parts
- Focuses on source code that needs fixing, not test files themselves
- Prevents regenerating tests when source code is the issue

**UTF-8 decoding with errors='replace'**
- Handles non-UTF-8 output from test runners gracefully
- Prevents decoding exceptions from blocking test execution
- Follows 03-RESEARCH.md executor pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully without issues.

## Next Phase Readiness

Test runner module complete and ready for integration into refinement loop. Next steps:
- Integrate execute_tests into code generation pipeline
- Implement refinement loop with test failure feedback to LLM
- Add retry logic with tenacity for API timeouts
- Extend PyGithub patterns for draft PRs and issue comments

No blockers. All must-haves verified:
- ✓ .booty.yml config loading with validation
- ✓ Subprocess execution with configurable timeout
- ✓ Exit code, stdout, stderr capture
- ✓ Zombie process cleanup on timeout
- ✓ File path and error summary extraction

---
*Phase: 03-test-driven-refinement*
*Completed: 2026-02-14*
