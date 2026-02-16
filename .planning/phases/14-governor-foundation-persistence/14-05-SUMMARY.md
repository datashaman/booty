---
phase: 14-governor-foundation-persistence
plan: 05
subsystem: ci
tags: [verify-main, workflow, verifier]

requires: []
provides:
  - booty verifier run (setup, install, test from .booty.yml)
  - verify-main.yml on push to main
affects: [15]

key-files:
  created: [.github/workflows/verify-main.yml]
  modified: [src/booty/cli.py]

duration: 5min
completed: 2026-02-16
---

# Phase 14 Plan 05: Verify-main Summary

**booty verifier run executes tests from .booty.yml; verify-main workflow runs on push to main**

## Accomplishments

- booty verifier run: loads .booty.yml, runs setup/install/test (reuses execute_tests)
- .github/workflows/verify-main.yml: on push to main, checkout, pip install, booty verifier run

---
*Phase: 14-governor-foundation-persistence*
*Completed: 2026-02-16*
