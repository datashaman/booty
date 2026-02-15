---
phase: 08-pull-request-webhook-verifier-runner
plan: 03
subsystem: verifier
tags: promotion, agent:builder, PR comments

provides:
  - agent:builder label on all Builder PRs
  - Builder never promotes (Verifier promotes agent PRs on success)
  - post_verifier_failure_comment for agent PR failures
  - Verifier calls promote_to_ready_for_review when agent PR and success

key-files:
  modified:
    - src/booty/github/pulls.py
    - src/booty/code_gen/generator.py
    - src/booty/github/comments.py
    - src/booty/verifier/runner.py

completed: 2026-02-15
---

# Phase 08 Plan 03: Builder Skip Promote + Verifier Promotion Summary

**Builder adds agent:builder to all PRs and never promotes; Verifier promotes on success, posts comment on failure**

## Accomplishments

- add_agent_builder_label in pulls.py; Builder calls it after create_pull_request for every PR
- Builder promotion block removed — Verifier owns promotion for agent PRs
- post_verifier_failure_comment in comments.py — updates single Verifier Results comment per PR
- runner.py: if agent PR and success → promote; if agent PR and failure → post comment (truncated stderr)

## Task Commits

1. **Task 1: Add agent:builder label and remove Builder promotion** — `77d57d4` (feat)
2. **Task 2: Verifier promotion and PR comment on failure** — `fa784f5` (feat)

## Files Created/Modified

- `src/booty/github/pulls.py` — add_agent_builder_label
- `src/booty/code_gen/generator.py` — add label, remove promote block
- `src/booty/github/comments.py` — post_verifier_failure_comment
- `src/booty/verifier/runner.py` — promote on success, comment on failure for agent PRs

## Deviations from Plan

None

## Issues Encountered

None

---
*Phase: 08-pull-request-webhook-verifier-runner*
*Completed: 2026-02-15*
