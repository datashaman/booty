---
phase: 24-lookup
plan: 01
subsystem: memory
tags: lookup, query, path-matching, fingerprint, memory

# Dependency graph
requires:
  - phase: 22
    provides: store.read_records, MemoryConfig, get_memory_state_dir
  - phase: 23
    provides: adapters.build_verifier_cluster_record fingerprint format
provides:
  - query(paths, repo, sha?, fingerprint?, config?, state_dir?, max_matches?) API
  - normalize_path, path_match_score, fingerprint_matches, derive_paths_hash
  - within_retention, repo_matches, sort_key, result_subset
affects: 25 (Surfacing), 26 (CLI)

# Tech tracking
tech-stack:
  added: []
  patterns: stdlib-only lookup, pathlib.PurePosixPath, in-memory filter+sort

key-files:
  created: src/booty/memory/lookup.py, tests/test_memory_lookup.py
  modified: src/booty/memory/__init__.py

key-decisions:
  - "Stdlib only; no new deps"
  - "verifier_cluster: derive paths_hash from candidate paths to match records when caller has paths"

patterns-established:
  - "Path normalization via PurePosixPath for repo paths"
  - "Multi-key sort: (severity_rank, -epoch, -path_overlap, id)"

# Metrics
duration: 5min
completed: 2026-02-16
---

# Phase 24 Plan 01: Deterministic Lookup Query Engine Summary

**Deterministic query engine with path/fingerprint matching, retention filter, severity-first sort — ready for Surfacing and CLI.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-16
- **Completed:** 2026-02-16
- **Tasks:** 3/3
- **Files modified:** 3

## Accomplishments

- `query(paths, repo, sha?, fingerprint?, config?, state_dir?, max_matches?)` returns matches from last 90 days
- Path intersection (prefix/containment) OR fingerprint match; additive
- verifier_cluster: derive paths_hash from candidate paths when caller has paths, no fingerprint
- Sort: severity desc, recency desc, path_overlap desc, id asc
- Result subset: type, timestamp, summary, links, id
- 13 pytest tests covering empty query, path match, fingerprint match, retention, repo filter, sort order, max_matches

## Task Commits

1. **Task 1: Path normalization and matching** — `57908ba` (feat)
2. **Task 2: Filter, sort, limit, result subset** — `57908ba` (feat)
3. **Task 3: query() API and tests** — `57908ba` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `src/booty/memory/lookup.py` — query(), normalize_path, path_match_score, fingerprint_matches, derive_paths_hash, within_retention, repo_matches, sort_key, result_subset
- `src/booty/memory/__init__.py` — export query
- `tests/test_memory_lookup.py` — 13 unit tests

## Decisions Made

None — followed plan and CONTEXT.md as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

Lookup API ready for Phase 25 (Surfacing) and Phase 26 (CLI).
