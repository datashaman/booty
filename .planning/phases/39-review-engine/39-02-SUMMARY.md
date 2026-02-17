---
phase: 39-review-engine
plan: 02
subsystem: reviewer
tags: runner, diff, magentic, check-run

# Dependency graph
requires:
  - phase: 39-01
    provides: run_review, ReviewResult, schema
provides:
  - process_reviewer_job with full LLM review
  - format_reviewer_comment(result) -> str
  - Check conclusion per REV-05 (approved / approved with suggestions / blocked)
  - PR comment with <!-- booty-reviewer --> marker
affects: 40

tech-stack:
  added: []
  patterns: asyncio.to_thread for sync run_review in async runner

key-files:
  created: tests/test_reviewer_runner.py
  modified: src/booty/reviewer/engine.py, src/booty/reviewer/runner.py

key-decisions:
  - "On LLM/infra failure: conclusion=failure, title='Reviewer error' (Phase 41 adds fail-open)"

patterns-established:
  - "Diff from repo.compare(base_sha, head_sha); concatenate file.patch"

duration: 12min
completed: 2026-02-17
---

# Phase 39: Review Engine — Plan 02 Summary

**Runner integration: diff fetch, run_review, format_reviewer_comment, check conclusion, PR comment posting**

## Performance

- **Duration:** ~12 min
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- format_reviewer_comment in engine.py per CONTEXT.md (header, rationale, 6 sections, marker)
- Runner fetches diff via repo.compare(base_sha, head_sha), builds pr_meta, calls run_review (asyncio.to_thread)
- Check conclusion: APPROVED → success "Reviewer approved"; APPROVED_WITH_SUGGESTIONS → success "Reviewer approved with suggestions"; BLOCKED → failure "Reviewer blocked"
- post_reviewer_comment with format_reviewer_comment body
- Error path: conclusion=failure, title="Reviewer error" (Phase 41 adds fail-open)
- 5 runner tests (format structure, APPROVED/BLOCKED flow, mock run_review)

## Task Commits

1. **Task 1+2: format_reviewer_comment, diff fetch, check conclusion, comment** - `293491d` (feat)
2. **Task 3: Runner integration tests** - `2dea022` (test)

## Files Created/Modified

- `src/booty/reviewer/engine.py` - format_reviewer_comment
- `src/booty/reviewer/runner.py` - diff fetch, run_review, check conclusion, post_reviewer_comment
- `tests/test_reviewer_runner.py` - 5 tests

## Decisions Made

None — followed plan as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- process_reviewer_job performs full LLM review
- Phase 40 (Promotion Gating) can require reviewer success for agent PRs

---
*Phase: 39-review-engine*
*Completed: 2026-02-17*
