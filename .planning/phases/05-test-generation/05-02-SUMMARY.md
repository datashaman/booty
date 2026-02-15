---
phase: 05-test-generation
plan: 02
subsystem: testing
tags: [llm, test-generation, prompts, validation, conventions]

# Dependency graph
requires:
  - phase: 05-01
    provides: Convention detection and import validation modules
provides:
  - LLM prompts extended with test generation instructions
  - Test file tracking in CodeGenerationPlan model
  - Full pipeline integration for test generation
affects: [future-builder-enhancements, test-generation-improvements]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Test files tracked separately from source changes (test_files field)
    - Test conventions passed through entire pipeline (detection -> generation -> refinement)
    - Import validation as safety signal (warnings, not hard gate)
    - Atomic commits include both source and test files

key-files:
  created: []
  modified:
    - src/booty/llm/models.py
    - src/booty/llm/prompts.py
    - src/booty/code_gen/generator.py
    - src/booty/code_gen/refiner.py

key-decisions:
  - "Test files tracked in separate test_files field (not mixed with changes)"
  - "Import validation logs warnings but doesn't block (refinement catches real failures)"
  - "Test files merged with changes before workspace apply (atomic commits)"
  - "Refinement prompt instructs LLM not to modify test files (one-shot test generation)"
  - "Empty test_conventions preserves original behavior (backward compatible)"

patterns-established:
  - "Template variables in magentic prompts handle optional sections (empty string = no-op)"
  - "Convention detection runs early in pipeline, before issue analysis"
  - "Test conventions forwarded through entire execution chain"

# Metrics
duration: 4 min
completed: 2026-02-15
---

# Phase 05 Plan 02: LLM Integration Summary

**Extended LLM prompts to generate tests alongside code using detected conventions, with full pipeline integration from detection through refinement**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-15T06:43:35Z
- **Completed:** 2026-02-15T06:47:56Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- CodeGenerationPlan now tracks test files separately from source changes
- LLM prompts include test generation instructions when conventions are detected
- Convention detection runs early in pipeline (after file listing, before analysis)
- Test file imports validated after generation (warnings logged for failures)
- Test files merged with changes for atomic commits
- Test conventions forwarded through refinement loop
- Refinement prompt instructs LLM not to modify test files

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend LLM models and prompts** - `2316a5a` (feat)
2. **Task 2: Wire detection and validation into pipeline** - `be73a76` (feat)

**Plan metadata:** (to be added in final commit)

## Files Created/Modified

- `src/booty/llm/models.py` - Added test_files field to CodeGenerationPlan
- `src/booty/llm/prompts.py` - Extended prompts with test_conventions parameter and test generation instructions
- `src/booty/code_gen/generator.py` - Integrated convention detection, import validation, and test file merging
- `src/booty/code_gen/refiner.py` - Added test_conventions forwarding to regeneration

## Decisions Made

**1. Test files in separate field (not mixed with changes)**
- Rationale: LLM needs clear separation to know which array to populate. Makes it explicit that tests are separate from source code changes.

**2. Import validation as warnings, not hard gate**
- Rationale: Import validation is a safety signal. Real failures will be caught by test execution in refinement loop. Blocking on warnings would prevent valid edge cases.

**3. Merge test files before workspace apply**
- Rationale: Ensures test files are written to disk and included in commit. Atomic changes - source and tests together.

**4. Refinement prompt: DO NOT modify test files**
- Rationale: Architectural decision from phase planning - one-shot test generation, refine only source code. Prevents refinement loop from breaking tests.

**5. Empty test_conventions preserves original behavior**
- Rationale: Backward compatibility. Repos with no detectable conventions work exactly as before (test_files will be empty list).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for:** Phase 6 (PR Promotion Criteria)

**What's complete:**
- Test generation fully integrated into Builder pipeline
- Convention detection, LLM prompts, import validation, and refinement all wired
- Test files included in same commit as source changes
- Backward compatible with repos that have no test conventions

**What's next:**
- PR promotion criteria (Phase 6: promote draft PRs to ready when tests pass AND linting passes)
- This completes v1.1 milestone (test generation + PR promotion)

**Notes:**
- Test generation is now fully functional end-to-end
- Builder will generate tests alongside code in a single LLM call
- Tests are validated, executed, and included in atomic commits
- Ready to add PR promotion as the final piece of v1.1

---
*Phase: 05-test-generation*
*Completed: 2026-02-15*
