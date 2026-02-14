---
phase: 03-test-driven-refinement
plan: 03
subsystem: testing
tags: [test-driven-development, refinement-loop, llm, tenacity, retry-logic, draft-pr]

# Dependency graph
requires:
  - phase: 03-01
    provides: Test execution infrastructure and config loading
  - phase: 03-02
    provides: Error parsing and file extraction from test output
provides:
  - Refinement loop integrating test execution with LLM regeneration
  - Targeted code regeneration prompt for fixing test failures
  - Draft PR creation for failed tests with error context
  - Failure notification comments on issues
  - End-to-end test-driven refinement pipeline
affects: [04-github-integration, future-deployment]

# Tech tracking
tech-stack:
  added: [tenacity (retry with exponential backoff)]
  patterns: [test-refine iteration loop, last-failure-only context, draft PR for failures]

key-files:
  created:
    - src/booty/code_gen/refiner.py
  modified:
    - src/booty/llm/prompts.py
    - src/booty/code_gen/generator.py
    - src/booty/main.py

key-decisions:
  - "Each refinement iteration sees only latest failure, not cumulative history"
  - "Fallback to all modified files if traceback doesn't identify specific failures"
  - "Tenacity retry for transient API errors (rate limit, timeout) with exponential backoff"
  - "Draft PR on test failure, normal PR on test success"
  - "Error message from refiner includes attempt context, no need to pass separately to comment"

patterns-established:
  - "Refinement loop pattern: test -> analyze -> regenerate -> repeat up to max_retries"
  - "Targeted regeneration: only regenerate files identified in failures"
  - "Final changes re-application: if regeneration occurs, re-apply to ensure consistency"
  - "Process_issue_to_pr returns tuple: (pr_number, tests_passed, error_message)"

# Metrics
duration: 3min
completed: 2026-02-14
---

# Phase 03 Plan 03: Test-Driven Refinement Loop Summary

**LLM-driven test refinement loop with targeted regeneration, retry logic, and draft PR creation for failures**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-14T14:16:50Z
- **Completed:** 2026-02-14T14:20:10Z
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- Refinement loop runs tests, analyzes failures, and regenerates affected files up to max_retries
- LLM prompt targets only failing files with error context for focused regeneration
- Transient API errors (rate limit, timeout) handled with exponential backoff via tenacity
- Test failures result in draft PR with error details plus issue comment notification
- Test success results in normal (ready) PR
- Missing .booty.yml fails job with clear error message

## Task Commits

Each task was committed atomically:

1. **Task 1: Add refinement prompt and create refiner module** - `7524b81` (feat)
2. **Task 2: Integrate refinement into pipeline and add failure handling** - `e62b1c9` (feat)

## Files Created/Modified

- `src/booty/code_gen/refiner.py` - Refinement loop: execute tests, extract errors, regenerate code, repeat
- `src/booty/llm/prompts.py` - Added regenerate_code_changes() prompt with UNTRUSTED delimiters and tenacity retry
- `src/booty/code_gen/generator.py` - Integrated refine_until_tests_pass, returns (pr_number, tests_passed, error_message), creates draft PR on failure
- `src/booty/main.py` - Unpacks new return type, posts failure comment on test failure

## Decisions Made

**Last-failure-only context:** Each refinement iteration passes only the latest test output to the LLM, not cumulative history. This keeps prompts focused and prevents context bloat.

**Fallback to all files:** If traceback parsing doesn't identify specific failing files, use all originally modified files as fallback to ensure something gets regenerated.

**Tenacity for API errors:** Wrap LLM calls with tenacity retry logic for RateLimitError, APITimeoutError, and asyncio.TimeoutError with exponential backoff (multiplier=1, min=4s, max=60s, max 5 attempts).

**Error message includes context:** Refiner formats error_message with "After N/M attempts..." prefix, so post_failure_comment doesn't need separate attempts/max_retries parameters (passed as 0, 0).

**Re-apply final changes:** If final_changes differ from plan.changes after refinement, re-apply them to workspace to ensure consistency before commit.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all imports and integrations worked as expected.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 3 (Test-Driven Refinement) is now complete. All three plans (03-01, 03-02, 03-03) have been executed:

- Test configuration and execution infrastructure (03-01)
- Error parsing and file extraction (03-02)
- Refinement loop and failure handling (03-03)

**Ready for Phase 4:** GitHub integration features and orchestration improvements can build on this complete test-driven refinement pipeline.

**No blockers:** The end-to-end pipeline works: issue → analysis → code generation → test refinement → PR creation (draft or ready based on test results) → failure notification.

---
*Phase: 03-test-driven-refinement*
*Completed: 2026-02-14*
