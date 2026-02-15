---
phase: 07-github-app-checks
plan: 03
subsystem: cli
tags: click, github-app, verifier

requires:
  - phase: 07-01
    provides: verifier_enabled, Settings
  - phase: 07-02
    provides: create_check_run

provides:
  - booty status (verifier: enabled|disabled)
  - booty verifier check-test (creates check run, prints check_run_id, url)
  - docs/github-app-setup.md
  - README Verifier section

key-files:
  created: [src/booty/cli.py, docs/github-app-setup.md, README.md]
  modified: [pyproject.toml]

key-decisions:
  - "booty = booty.cli:main; server runs via uvicorn booty.main:app"
  - "status falls back to env check when full Settings fails (e.g. missing WEBHOOK_SECRET)"

duration: 15min
completed: 2026-02-15
---

# Phase 7 Plan 03: CLI + Docs Summary

**CLI with booty status and booty verifier check-test; docs/github-app-setup.md; README Verifier section.**

## Performance

- **Tasks:** 3
- **Files modified:** 4 (cli.py, pyproject.toml, docs, README)

## Accomplishments

- booty status prints verifier: enabled|disabled
- booty verifier check-test --repo owner/repo --sha SHA --installation-id ID
- Output: check_run_id, installation_id, repo, sha, status, url
- docs/github-app-setup.md: create/use/install/configure/verify sections
- README: Verifier blurb, quick verify command, link to docs

## Task Commits

1. **Task 1: Add CLI** - `9f8b12e` (feat)
2. **Task 2: docs/github-app-setup.md** - (docs, in d48bfc2)
3. **Task 3: README section** - `d48bfc2` (docs)

## Files Created/Modified

- `src/booty/cli.py` - click CLI: status, verifier check-test
- `pyproject.toml` - click dependency, booty = booty.cli:main
- `docs/github-app-setup.md` - Step-by-step App setup
- `README.md` - Verifier section, quick verify

## Decisions Made

- status command: catch Settings validation error, fall back to GITHUB_APP_* env check
- --dry-run on check-test for input validation without creating check

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None

## Next Phase Readiness

Phase 7 complete. Manual test: booty verifier check-test with real credentials creates check visible in GitHub UI.

---
*Phase: 07-github-app-checks*
*Completed: 2026-02-15*
