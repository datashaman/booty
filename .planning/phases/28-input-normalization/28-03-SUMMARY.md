---
phase: 28-input-normalization
plan: 03
subsystem: planner
tags: worker, cli, normalizers, wiring

requires:
  - phase: 28-01
    provides: PlannerInput, normalizers
  - phase: 28-02
    provides: get_repo_context
provides:
  - process_planner_job consumes PlannerInput via normalize_from_job
  - plan_issue uses normalize_github_issue with full issue
  - plan_text uses normalize_cli_text with optional repo inference
affects: [29]

tech-stack:
  added: []
  patterns: [normalizer-first flow, optional repo context when token available]

key-files:
  created: []
  modified: [src/booty/planner/worker.py, src/booty/cli.py]

key-decisions:
  - "plan_text infers repo from cwd when in git repo; --repo optional"
  - "plan_path_for_ad_hoc(text) kept for path uniqueness"

patterns-established:
  - "Worker/CLI build Plan from PlannerInput.goal; full PlannerInput ready for Phase 29"

duration: ~8min
completed: 2026-02-16
---

# Phase 28: Input Normalization Plan 03 Summary

**Worker and CLI wired to input normalizers; Plan built from PlannerInput.goal; optional repo context when repo + token available**

## Performance

- **Duration:** ~8 min
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- process_planner_job: normalize_from_job + get_repo_context when owner/repo/token available
- plan_issue: full issue dict → normalize_github_issue → goal; repo_context when token present
- plan_text: normalize_cli_text; repo inferred from cwd or --repo; plan_path_for_ad_hoc(text) unchanged

## Task Commits

1. **Task 1: Wire worker** - `8698eb1` (feat)
2. **Task 2+3: Wire CLI** - `2a37182` (feat)

## Files Modified

- `src/booty/planner/worker.py` - normalize_from_job, get_repo_context
- `src/booty/cli.py` - plan_issue, plan_text use normalizers

## Deviations from Plan

None - plan executed exactly as written

## Verification

- booty plan text "First line\nRest" → goal="First line" ✓
- booty plan text "Single" → goal="Single" ✓
- All 200 tests pass

## Next Phase Readiness

- Phase 29 can consume full PlannerInput (goal, body, labels, source_type, repo_context)
- Plan still minimal (steps=[]); Phase 29 does generation

---
*Phase: 28-input-normalization*
*Completed: 2026-02-16*
