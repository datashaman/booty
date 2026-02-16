# Plan 31-01: Cache Primitives — Complete

**Status:** ✓ Complete
**Completed:** 2026-02-16

## Deliverables

- **Plan metadata field** — `Plan.metadata: dict` in schema.py for created_at, input_hash, plan_hash
- **cache.py** — input_hash, plan_hash, is_plan_fresh, find_cached_issue_plan
- **store.py** — load_plan(path) -> Plan | None
- **Tests** — tests/test_planner_cache.py (9 tests, all pass)

## Key Implementation

- `input_hash(PlannerInput)` — canonical dict: goal, body, sorted labels, source_type, incident_fields, default_branch; SHA-256 of JSON
- `plan_hash(Plan)` — hashes model_dump excluding metadata
- `is_plan_fresh(created_at, ttl_hours)` — UTC-aware TTL check
- `find_cached_issue_plan(owner, repo, issue_number, input_hash, ttl_hours)` — load, validate input_hash match, check freshness

## Commits

- feat(31-01): schema metadata, cache primitives, load_plan
- test(31-01): planner cache unit tests
