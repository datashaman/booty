---
phase: 35-idempotency
plan: 02
subsystem: github
tags: comments, diff, booty-plan, booty-architect

requires: []
provides:
  - get_plan_comment_body
  - update_plan_comment_with_architect_section_if_changed
affects: plan 35-03 (main flow uses diff-before-update)

key-files:
  created: tests/test_github_comments.py
  modified: src/booty/github/comments.py

key-decisions:
  - "Diff exact string: extract existing block via regex, compare before update"
  - "Return False when unchanged (no GitHub API call)"

duration: 4min
completed: 2026-02-17
---

# Phase 35 Plan 02: Comment Diff Helper Summary

**get_plan_comment_body and update_plan_comment_with_architect_section_if_changed for ARCH-25**

## Accomplishments

- get_plan_comment_body: returns body of comment containing <!-- booty-plan --> or None
- update_plan_comment_with_architect_section_if_changed: fetches body, extracts existing booty-architect block, compares; updates only when different
- 4 tests: found/not-found, skips when identical, calls when different

## Task Commits

1. **Task 1-2: Add get_plan_comment_body, update_plan_comment_with_architect_section_if_changed** - feat
2. **Task 3: Add tests** - test

## Files Created/Modified

- `src/booty/github/comments.py` - get_plan_comment_body, update_plan_comment_with_architect_section_if_changed
- `tests/test_github_comments.py` - 4 tests

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

Ready for 35-03 (main flow integration).
