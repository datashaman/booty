# Plan 31-03: Ad-hoc Cache — Complete

**Status:** ✓ Complete
**Completed:** 2026-02-16

## Deliverables

- **Ad-hoc cache** — plan_path_for_ad_hoc_from_input, find_cached_ad_hoc_plan, save_ad_hoc_plan; hash index at plans/ad-hoc/index.json
- **CLI plan_text** — checks find_cached_ad_hoc_plan before LLM; on hit shows "(cached, created at …)"
- **Tests** — 4 ad-hoc cache tests in test_planner_cache.py

## Key Implementation

- Index maps input_hash → filename; lookup by hash, not directory
- Timestamped paths (microsecond precision) preserve history; index points to latest
- save_ad_hoc_plan adds created_at if missing for find_cached_ad_hoc_plan validation
