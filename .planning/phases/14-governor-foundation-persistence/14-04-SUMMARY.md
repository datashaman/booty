---
phase: 14-governor-foundation-persistence
plan: 04
subsystem: deploy
tags: [workflow_dispatch, deploy, sha]

requires: []
provides:
  - deploy.yml sha input for workflow_dispatch
  - deploy.sh DEPLOY_SHA support
affects: [15]

key-files:
  created: []
  modified: [.github/workflows/deploy.yml, deploy.sh]

duration: 3min
completed: 2026-02-16
---

# Phase 14 Plan 04: Deploy sha input Summary

**Deploy workflow accepts optional sha input; deploy.sh checks out DEPLOY_SHA when set**

## Accomplishments

- workflow_dispatch inputs.sha; preflight fails if workflow_dispatch without sha
- Checkout ref: inputs.sha || github.sha
- DEPLOY_SHA env passed to deploy step and deploy.sh
- deploy.sh: when DEPLOY_SHA set, git fetch + checkout; else pull branch

---
*Phase: 14-governor-foundation-persistence*
*Completed: 2026-02-16*
