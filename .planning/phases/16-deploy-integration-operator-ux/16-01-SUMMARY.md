---
phase: 16-deploy-integration-operator-ux
plan: 01
subsystem: infra
tags: PyGithub, workflow_dispatch, commit-status, release-governor

requires: []
provides:
  - dispatch_deploy in deploy.py
  - post_hold_status, post_allow_status in ux.py
  - Webhook ALLOW/HOLD integration (dispatch + status on decision)
affects: phase-17

key-files:
  created: src/booty/release_governor/deploy.py, src/booty/release_governor/ux.py
  modified: src/booty/webhooks.py

completed: "2026-02-16"
---

# Phase 16 Plan 01: Deploy Trigger & HOLD/ALLOW UX Summary

**workflow_dispatch deploy trigger with sha input, commit status for HOLD/ALLOW (booty/release-governor)**

## Accomplishments
- deploy.py: dispatch_deploy triggers deploy workflow via workflow_dispatch with sha input (GOV-14, GOV-18)
- ux.py: post_hold_status (state=failure) and post_allow_status (state=success), context=booty/release-governor
- Webhook integration: on ALLOW → dispatch_deploy, update state, append_deploy_to_history, post_allow_status
- On HOLD → post_hold_status with reason-specific "how to unblock" and approval_mode hint for high_risk_no_approval

## Task Commits
1. **Task 1+2: deploy.py, ux.py** - `816b90a` (feat)
2. **Task 3: Webhook integration** - `7203366` (feat)

## Deviations from Plan
None - plan executed as specified.

## Issues Encountered
None

---
*Phase: 16-deploy-integration-operator-ux*
*Completed: 2026-02-16*
