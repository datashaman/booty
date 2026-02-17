---
phase: 41-fail-open-metrics
plan: 03
subsystem: reviewer
tags: [cli, docs, reviewer-status]

requires:
  - phase: 41-02
    provides: metrics and structured logs
provides:
  - booty reviewer status command with --json
  - capabilities-summary Reviewer CLI/metrics line
  - reviewer.md: Fail-open, Metrics, CLI, Troubleshooting
affects: []

tech-stack:
  added: []
  patterns: [Architect-style CLI group]

key-files:
  created: []
  modified: [src/booty/cli.py, docs/capabilities-summary.md, docs/reviewer.md]

key-decisions: []

duration: ~5min
completed: 2026-02-17
---

# Phase 41 Plan 03: CLI and Docs Summary

**booty reviewer status CLI reading from persisted metrics, and docs: fail-open semantics, metrics names, troubleshooting checklist.**

## Performance

- **Duration:** ~5 min
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Reviewer Click group with status command (--repo, --workspace, --json)
- Reads get_reviewer_24h_stats from persisted metrics (not logs)
- capabilities-summary: "CLI: booty reviewer status. Persisted metrics: reviews_total, reviews_blocked, reviews_suggestions, reviewer_fail_open."
- reviewer.md: Fail-open section (buckets, check output, no comment), Metrics section (~/.booty/state/reviewer/metrics.json), CLI section, Troubleshooting (token, diff fetch, LLM timeout)

## Task Commits

1. **Task 1: Add booty reviewer status command** - `8f742da` (feat, with docs)
2. **Task 2: Update capabilities-summary and reviewer.md** - (same commit)

## Files Created/Modified

- `src/booty/cli.py` - reviewer group, status command
- `docs/capabilities-summary.md` - Reviewer CLI and metrics line
- `docs/reviewer.md` - Fail-open, Metrics, CLI, Troubleshooting sections

## Decisions Made

None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Phase 41 complete. Ready for milestone completion.

---
*Phase: 41-fail-open-metrics*
*Completed: 2026-02-17*
