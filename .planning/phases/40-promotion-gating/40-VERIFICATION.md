---
phase: 40-promotion-gating
verified: 2026-02-17
status: passed
---

# Phase 40: Promotion Gating — Verification

**Status:** passed

## Must-Haves Check

### Truths

| Must-Have | Status | Evidence |
|-----------|--------|----------|
| Agent PR promoted only when booty/verifier success AND (Reviewer disabled OR booty/reviewer success) | ✓ | runner.py:507-540 — can_promote=True by default; when reviewer_enabled and repo, can_promote=reviewer_check_success(); promote only if can_promote |
| When Reviewer enabled and booty/reviewer not yet success, Verifier exits with check success but does NOT promote | ✓ | runner.py:518-526 — if not can_promote, log promotion_waiting_reviewer; promote block is inside `if can_promote` |
| Non-agent PRs unchanged; fail-open success (Phase 41) counts as success | ✓ | All promotion logic inside `if job.is_agent_pr`; fail-open not yet implemented (Phase 41) |

### Artifacts

| Path | Provides | Status | Evidence |
|------|----------|--------|----------|
| src/booty/github/checks.py | reviewer_check_success helper | ✓ | reviewer_check_success() at L156; uses get_check_runs via commit.get_check_runs() |
| src/booty/verifier/runner.py | Promotion gate using reviewer check | ✓ | get_reviewer_config, apply_reviewer_env_overrides, reviewer_check_success, can_promote gate |

### Key Links

| From | To | Via | Status |
|------|-----|-----|--------|
| verifier/runner.py | github/checks.py | reviewer_check_success | ✓ L16 import, L520 call |
| verifier/runner.py | reviewer/config.py | get_reviewer_config, apply_reviewer_env_overrides | ✓ L42-43 import, L511-514 call |

## Summary

All must-haves verified against codebase. Promotion gate implemented: when Reviewer enabled, Verifier requires booty/reviewer success before promoting agent PRs. REV-14 satisfied.
