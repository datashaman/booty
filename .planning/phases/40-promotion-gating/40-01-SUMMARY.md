---
phase: 40-promotion-gating
plan: 01
subsystem: infra
tags: [github-checks, reviewer, verifier, promotion, pygithub]

requires:
  - phase: 39-review-engine
    provides: Reviewer check run lifecycle, block_on mapping
provides:
  - reviewer_check_success helper in checks.py
  - Verifier promotion gated on booty/reviewer success when Reviewer enabled
affects: [41-fail-open-metrics]

tech-stack:
  added: []
  patterns: [Promotion gate: get_reviewer_config + reviewer_check_success before promote]

key-files:
  created: []
  modified: [src/booty/github/checks.py, src/booty/verifier/runner.py, tests/test_github_checks.py]

key-decisions:
  - "Use repo.get_commit(head_sha).get_check_runs() — PyGithub exposes get_check_runs on Commit, not Repository"
  - "ReviewerConfigError → reviewer_enabled=False (fail closed on config error per decisions)"

patterns-established:
  - "Promotion gate: Before promote, check reviewer_enabled; if enabled, require reviewer_check_success"

duration: ~15min
completed: 2026-02-17
---

# Phase 40: Promotion Gating Summary

**Verifier promotion gated on booty/reviewer success when Reviewer enabled — agent PRs require both checks before draft→ready-for-review**

## Performance

- **Duration:** ~15 min
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- `reviewer_check_success(repo, head_sha)` helper in checks.py — returns True only when booty/reviewer has status completed and conclusion success
- Verifier promotion logic: when Reviewer enabled, call reviewer_check_success before promote; if False, skip promote and log promotion_waiting_reviewer
- Five tests covering success, no runs, in_progress, failure, exception cases

## Task Commits

1. **Task 1: Add reviewer_check_success helper** - `9e26bca` (feat)
2. **Task 2: Gate Verifier promotion on reviewer when enabled** - `47b08d2` (feat)
3. **Task 3: Add test for reviewer_check_success** - `8134c7c` (test)

## Files Created/Modified

- `src/booty/github/checks.py` — reviewer_check_success helper using repo.get_commit().get_check_runs()
- `src/booty/github/__init__.py` — export reviewer_check_success
- `src/booty/verifier/runner.py` — Promotion gate: get_reviewer_config, apply_reviewer_env_overrides, reviewer_check_success
- `tests/test_github_checks.py` — 5 reviewer_check_success tests

## Decisions Made

- PyGithub exposes get_check_runs on Commit, not Repository. Used repo.get_commit(head_sha).get_check_runs(check_name="booty/reviewer") instead of repo.get_check_runs(head_sha=...).

## Deviations from Plan

None — plan executed as written. Minor implementation detail: PyGithub API differs from research assumption (get_check_runs on Commit vs Repository) but behavior matches.

## Issues Encountered

None

## Next Phase Readiness

- Promotion gate complete; Phase 41 (Fail-Open + Metrics) can add fail-open handling and metrics
- REV-14 satisfied: Builder (via Verifier) requires both booty/verifier and booty/reviewer success for agent PRs when Reviewer enabled

---
*Phase: 40-promotion-gating*
*Completed: 2026-02-17*
