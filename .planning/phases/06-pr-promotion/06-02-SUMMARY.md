---
phase: 06-pr-promotion
plan: 02
subsystem: pipeline
tags: [quality, promotion, generator, self-modification]

# Dependency graph
requires:
  - phase: 06-01
    provides: promote_to_ready_for_review, post_promotion_failure_comment
provides:
  - Quality checks run for all jobs (promotion gate)
  - Draft PR promoted when tests+lint pass and not self-modification
  - Self-modification PRs always draft with explicit note
affects: [v1.1-complete]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Quality gate before promotion decision (all jobs)
    - Promote after PR creation when should_promote
    - Self-mod PR body: "Draft by design" note in Safety Summary

key-files:
  created: []
  modified:
    - src/booty/code_gen/generator.py
    - src/booty/github/pulls.py

key-decisions:
  - "Always create PRs as draft; promote when criteria met"
  - "should_promote = tests_passed and quality_passed and not is_self_modification"
  - "On promotion exception: post failure comment, do not fail job"
  - "Self-mod PR body: explicit 'Draft by design' in Safety Summary"

patterns-established:
  - "Quality checks run for all jobs (not self-mod-only)"
  - "Promotion is post-PR step, not part of create_pull_request"

# Metrics
duration: 5min
completed: 2026-02-15
---

# Phase 06 Plan 02: Pipeline Wiring Summary

**Quality for all jobs, always-draft PRs, promotion when criteria met**

## Performance

- **Duration:** 5 min
- **Completed:** 2026-02-15
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Quality checks run for ALL jobs (removed is_self_modification guard)
- Quality failures set tests_passed=False and append to error_message
- PR creation: always draft (is_draft=True)
- Promotion step after PR creation: promote when tests+quality pass and not self-mod
- Promotion failure: post neutral comment, leave PR draft
- Self-modification PR body: "Draft by design: Self-modification PRs are not auto-promoted" in Safety Summary
- Pipeline docstring updated for step 10b and 13

## Verification

- run_quality_checks called outside is_self_modification block
- promote_to_ready_for_review, post_promotion_failure_comment, should_promote in generator
- ruff check passes on modified files

## Success Criteria Met

- Quality checks run for all jobs
- Draft PR promoted when tests passed, quality passed, not self-modification
- Promotion failure posts comment, leaves PR draft
- Self-modification PRs never promoted

---
*Phase: 06-pr-promotion | Plan: 02 | Completed: 2026-02-15*
