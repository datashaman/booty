---
phase: 39-review-engine
plan: 01
subsystem: reviewer
tags: magentic, pydantic, llm, review

# Dependency graph
requires:
  - phase: 38-agent-pr-detection-event-wiring
    provides: ReviewerJob, runner stub, check lifecycle
provides:
  - ReviewResult, CategoryResult, Finding, ReviewDecision
  - run_review(diff, pr_meta, block_on) -> ReviewResult
  - Magentic prompt producing 6 category grades
  - block_on mapping (overengineering, poor_tests, duplication, architectural_regression)
affects: 39-02

tech-stack:
  added: []
  patterns: Magentic @prompt with Pydantic return, block_on config mapping

key-files:
  created: src/booty/reviewer/schema.py, prompts.py, engine.py, tests/test_reviewer_engine.py
  modified: src/booty/reviewer/__init__.py

key-decisions:
  - "LLM returns _ReviewLLMOutput with categories; engine applies block_on to compute decision"
  - "block_on empty → max APPROVED_WITH_SUGGESTIONS; only 4 categories can block"

patterns-established:
  - "Same Magentic @prompt pattern as planner/generation.py"
  - "BLOCK_ON_TO_CATEGORY explicit map; unknown keys ignored"

duration: 15min
completed: 2026-02-17
---

# Phase 39: Review Engine — Plan 01 Summary

**Review schema, Magentic LLM prompt, block_on mapping, and decision logic for run_review**

## Performance

- **Duration:** ~15 min
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- schema.py: ReviewResult, CategoryResult, Finding, ReviewDecision; 6 fixed categories
- prompts.py: Magentic @prompt with diff, pr_meta, file_list; quality-only evaluation
- engine.py: run_review with BLOCK_ON_TO_CATEGORY, decision logic, diff truncation (80k)
- 5 tests for block_on mapping, empty block_on, non-blocking categories, all-PASS, WARN

## Task Commits

1. **Task 1: Review schema and output models** - `7d12ad4` (feat)
2. **Task 2: Magentic prompt and run_review** - `fc6e66d` (feat)
3. **Task 3: Tests for decision logic** - `9c61580` (test)

## Files Created/Modified

- `src/booty/reviewer/schema.py` - Pydantic models for LLM output and engine result
- `src/booty/reviewer/prompts.py` - Magentic prompt for diff-based review
- `src/booty/reviewer/engine.py` - run_review, block_on mapping, decision logic
- `src/booty/reviewer/__init__.py` - Export ReviewResult, run_review
- `tests/test_reviewer_engine.py` - 5 decision logic tests (mocked LLM)

## Decisions Made

None — followed plan as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- run_review ready for 39-02 runner integration
- format_reviewer_comment to be added in 39-02

---
*Phase: 39-review-engine*
*Completed: 2026-02-17*
