---
phase: 28-input-normalization
plan: 02
subsystem: planner
tags: pygithub, repo-context, default-branch, tree

requires:
  - phase: 28-01
    provides: PlannerInput, normalizers with repo_context param
provides:
  - get_repo_context(owner, repo, token, max_depth=2) -> dict | None
  - default_branch and tree (2 levels) for PlannerInput.repo_context
affects: [28-03]

tech-stack:
  added: []
  patterns: [PyGithub get_contents recursive, graceful None on error]

key-files:
  created: []
  modified: [src/booty/planner/input.py, tests/test_planner_input.py]

key-decisions:
  - "Graceful None on GithubException (404, auth)"
  - "max_depth=2 gives root + 2 levels of dirs"

patterns-established:
  - "get_repo_context returns {default_branch, tree} or None"

duration: ~5min
completed: 2026-02-16
---

# Phase 28: Input Normalization Plan 02 Summary

**get_repo_context fetches default branch and shallow file tree; normalizers pass repo_context through**

## Performance

- **Duration:** ~5 min
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- get_repo_context(owner, repo, token, max_depth=2) in input.py
- Uses PyGithub get_contents with recursive depth limit
- Returns None on GithubException (404, auth errors)
- Verified normalizers accept and pass repo_context (28-01 already correct)

## Task Commits

1. **Task 1: get_repo_context** - `f48ad90` (feat)
2. **Task 2: Test for None on error** - `c853e2e` (test)

## Files Modified

- `src/booty/planner/input.py` - get_repo_context
- `tests/test_planner_input.py` - test_get_repo_context_returns_none_on_invalid_token

## Deviations from Plan

None - plan executed exactly as written

## Next Phase Readiness

- 28-03 can wire worker/CLI to call get_repo_context when repo+token available

---
*Phase: 28-input-normalization*
*Completed: 2026-02-16*
