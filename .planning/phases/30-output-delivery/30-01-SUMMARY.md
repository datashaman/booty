---
phase: 30-output-delivery
plan: 01
subsystem: planner
tags: [planner, github, comments, markdown]

requires:
  - phase: 29
    provides: Plan schema, generate_plan, save_plan
provides:
  - format_plan_comment(plan) -> str for GitHub issue comments
  - post_plan_comment(github_token, repo_url, issue_number, body) with find-and-edit
affects: [30-02 worker CLI wiring]

tech-stack:
  added: []
  patterns: [find-and-edit comment pattern, operator-focused markdown]

key-files:
  created: [src/booty/planner/output.py, tests/test_planner_output.py]
  modified: [src/booty/github/comments.py]

key-decisions:
  - pr_body_outline collapsed when >200 chars or multiple newlines
  - Empty handoff fields omitted from Builder instructions

patterns-established:
  - Plan comment format: Goal → Risk → Steps → Builder instructions → collapsed JSON
  - <!-- booty-plan --> marker for find-and-edit

duration: 15min
completed: 2026-02-16
---

# Phase 30-01: Plan Comment Formatter Summary

**format_plan_comment and post_plan_comment for single-issue plan comments with find-and-edit**

## Performance

- **Duration:** ~15 min
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- format_plan_comment(plan) produces markdown per 30-CONTEXT (Goal, Risk, Steps, Builder instructions, collapsed JSON)
- post_plan_comment mirrors post_memory_comment: find existing <!-- booty-plan -->, edit or create
- Empty handoff fields omitted; long pr_body_outline in <details>
- Tests for sections, marker, empty omission, long pr_body collapse

## Task Commits

1. **Task 1: format_plan_comment** - `6e383ad` (feat)
2. **Task 2: post_plan_comment** - `df89c33` (feat)
3. **Task 3: Tests** - `11c188e` (test)

## Files Created/Modified

- `src/booty/planner/output.py` - format_plan_comment with _step_line, _builder_bullets
- `src/booty/github/comments.py` - post_plan_comment with find-and-edit
- `tests/test_planner_output.py` - 4 tests (sections, marker, empty handoff, long pr_body)

## Decisions Made

None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

---
*Phase: 30-output-delivery*
*Completed: 2026-02-16*
