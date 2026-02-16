---
phase: 16-deploy-integration-operator-ux
plan: 03
subsystem: infra
tags: workflow_run, deploy-outcome, release-governor

requires:
  - phase: 16-02
    provides: create_or_append_deploy_failure_issue
provides:
  - Deploy workflow_run branch in webhooks
  - production_sha update on success
  - Failure issue creation on failure/cancelled
affects: phase-17

key-files:
  modified: src/booty/webhooks.py

completed: "2026-02-16"
---

# Phase 16 Plan 03: Deploy Outcome Observation Summary

**Governor observes deploy workflow_run completion; updates state; creates issues on failure**

## Accomplishments
- workflow_run routing: check deploy workflow BEFORE verification (by path.endswith or name match)
- Deploy branch: action=completed, workflow matches deploy_workflow_name
- On success: production_sha_current/previous updated, append_deploy_to_history(success)
- On failure/cancelled: create_or_append_deploy_failure_issue, append_deploy_to_history(failure)
- Idempotency: deploy_run_{workflow_run_id} key for delivery_ids
- Verification branch unchanged: conclusion=success, head_branch=main, verification_workflow_name

## Task Commits
1. **Task 1: Deploy workflow_run branch** - `7203366` (feat)

## Deviations from Plan
None - plan executed as specified.

## Issues Encountered
None

---
*Phase: 16-deploy-integration-operator-ux*
*Completed: 2026-02-16*
