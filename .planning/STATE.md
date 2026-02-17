# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-17)

**Core value:** A Builder agent that can take a GitHub issue and produce a working PR with tested code — the foundation everything else builds on.
**Current focus:** Phase 38 — Agent PR Detection + Event Wiring

## Current Position

Phase: 37 (Complete)
Plan: 37-01, 37-02, 37-03
Status: Phase 37 complete; verified
Last activity: 2026-02-17 — Phase 37 executed and verified

## Accumulated Context

### Decisions

- Reviewer disabled by default when block missing (avoid surprising required checks on existing repos)
- Fail-open: quality tooling never halts delivery due to infra issues
- REVIEWER_ENABLED env wins over file config
- Unknown reviewer keys fail Reviewer only (do not break Verifier/Security)

See PROJECT.md Key Decisions table for full history.

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-17
Stopped at: Phase 37 complete
Next step: `/gsd:discuss-phase 38` or `/gsd:plan-phase 38`
