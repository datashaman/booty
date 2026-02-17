---
phase: 33-validation-rules
status: passed
verified: 2026-02-17
---

# Phase 33: Validation Rules — Verification

**Phase Goal:** Structural integrity, path consistency, risk accuracy, ambiguity and overreach detection.

## must_haves

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Architect validates steps ≤ 12; each step has id + action; actions ∈ {read, add, edit, run, verify, research} | ✓ | validation.py validate_structural; test_architect_validation |
| 2 | touch_paths == union(step.paths); empty paths flagged unless justified | ✓ | derive_touch_paths, validate_paths with flags |
| 3 | Risk recomputed from touch_paths (HIGH/MEDIUM/LOW); Architect overrides Planner when different | ✓ | compute_risk_from_touch_paths, ensure_touch_paths_and_risk |
| 4 | Ambiguous steps rewritten when rewrite_ambiguous_steps enabled | ✓ | rewrite_ambiguous_steps in rewrite.py |
| 5 | Overreach detected (repo-wide, multi-domain); rewritten into smaller scope when possible | ✓ | check_overreach, try_rewrite_overreach |
| 6 | Architect completes in < 5 seconds | ✓ | test_process_architect_input_completes_under_5_seconds |

## human_verification

None required — all checks automated.

## gaps

None.
