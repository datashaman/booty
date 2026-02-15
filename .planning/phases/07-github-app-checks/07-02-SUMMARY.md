---
phase: 07-github-app-checks
plan: 02
subsystem: auth
tags: pygithub, github-app, checks-api

requires:
  - phase: 07-01
    provides: GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY, verifier_enabled

provides:
  - create_check_run (booty/verifier) via GitHub App auth
  - get_verifier_repo for App-authenticated Repository
  - edit_check_run for lifecycle transitions

key-files:
  created: [src/booty/github/checks.py]
  modified: [src/booty/github/__init__.py]

key-decisions:
  - "get_verifier_repo returns None on auth failure (log and continue per CONTEXT)"
  - "PEM normalization: replace \\n with newlines before Auth.AppAuth"

duration: 12min
completed: 2026-02-15
---

# Phase 7 Plan 02: checks.py Summary

**checks.py with create_check_run, get_verifier_repo, edit_check_run — all use GitHub App auth; booty/verifier check run name.**

## Performance

- **Tasks:** 2
- **Files modified:** 2 (created checks.py, updated __init__.py)

## Accomplishments

- get_verifier_repo(owner, repo_name, installation_id, settings) → Repository | None
- create_check_run with status, output, details_url; returns None when Verifier disabled
- edit_check_run(check_run, status, conclusion, output) for lifecycle
- Exported in github/__init__.py

## Task Commits

1. **Task 1: Create checks.py with App auth and create_check_run** - (feat)
2. **Task 2: Add edit_check_run helper** - (feat)
- **Combined:** Single commit for checks.py + __init__.py

## Files Created/Modified

- `src/booty/github/checks.py` - create_check_run, get_verifier_repo, edit_check_run
- `src/booty/github/__init__.py` - Export create_check_run, edit_check_run, get_verifier_repo

## Decisions Made

- Return None (not raise) on auth failure — "log error and continue" per CONTEXT
- Reason classification: auth_failed, bad_key, jwt_failed for structured logging

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

checks.py ready for CLI (booty verifier check-test) in Wave 3.

---
*Phase: 07-github-app-checks*
*Completed: 2026-02-15*
