# Phase 31: Idempotency — Verification

**Status:** passed
**Verified:** 2026-02-16

## Phase Goal

Same plan for unchanged inputs within 24h; plan_hash for dedup.

## Must-Haves Verified

| Check | Status |
|-------|--------|
| Planner checks for existing plan for same issue within 24h | ✓ |
| If inputs unchanged, return cached plan (no new LLM call) | ✓ |
| Plan metadata includes plan_hash (hash of normalized plan) | ✓ |
| Output is reproducible for unchanged inputs | ✓ |

## Evidence

- **Worker:** process_planner_job calls find_cached_issue_plan before generate_plan; cache hit skips LLM
- **CLI plan_issue:** checks find_cached_issue_plan before generate_plan
- **CLI plan_text:** checks find_cached_ad_hoc_plan before generate_plan; shows "(cached, created at …)" on hit
- **Metadata:** created_at, input_hash, plan_hash merged on every save (worker, plan_issue, plan_text)
- **cache.py:** input_hash, plan_hash, find_cached_issue_plan, find_cached_ad_hoc_plan, save_ad_hoc_plan
- **store.py:** load_plan, plan_path_for_ad_hoc_from_input
- **Tests:** 13 cache tests pass
