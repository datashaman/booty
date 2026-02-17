---
phase: 37-skeleton-check-plumbing
plan: 02
subsystem: reviewer
tags: github-checks, booty-reviewer

requires:
  - phase: 37-01
    provides: ReviewerConfig, get_reviewer_config
provides:
  - create_reviewer_check_run in github/checks.py
  - booty/reviewer check run lifecycle (queued → in_progress → completed via edit_check_run)
affects: [38]

tech-stack:
  added: []
  patterns: [GitHub App check run, same auth as Verifier]

key-files:
  created: [tests/test_github_checks.py]
  modified: [src/booty/github/checks.py]

key-decisions:
  - "Uses get_verifier_repo — same GitHub App as Verifier"
  - "Returns None when App credentials missing"

patterns-established:
  - "create_reviewer_check_run mirrors create_security_check_run"

duration: 3min
completed: 2026-02-17
---

# Phase 37-02: create_reviewer_check_run Summary

**create_reviewer_check_run for booty/reviewer check run lifecycle (REV-04)**

## Performance

- **Duration:** ~3 min
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- create_reviewer_check_run in checks.py
- name="booty/reviewer", output default {"title": "Booty Reviewer", "summary": "Queued for review…"}
- Returns None when get_verifier_repo returns None (App disabled)
- 2 tests: app disabled returns None, create_check_run called with correct args

## Task Commits

1. **Task 1: create_reviewer_check_run** - `fe7c5c8` (feat)
2. **Task 2: Tests for create_reviewer_check_run** - `e733c45` (test)

## Files Created/Modified

- `src/booty/github/checks.py` - create_reviewer_check_run
- `tests/test_github_checks.py` - 2 tests

## Decisions Made

None — plan executed exactly as specified

## Deviations from Plan

None - plan executed exactly as written

## Issues Encountered

None

## Next Phase Readiness

- create_reviewer_check_run ready for Phase 38 webhook wiring
- edit_check_run (existing) used for status/conclusion updates

---
*Phase: 37-skeleton-check-plumbing*
*Completed: 2026-02-17*
