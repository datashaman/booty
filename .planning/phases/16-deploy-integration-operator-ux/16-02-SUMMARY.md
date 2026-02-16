---
phase: 16-deploy-integration-operator-ux
plan: 02
subsystem: infra
tags: PyGithub, GitHub-issues, deploy-failure, release-governor

requires: []
provides:
  - create_or_append_deploy_failure_issue in failure_issues.py
affects: phase-16-plan-03

key-files:
  created: src/booty/release_governor/failure_issues.py

completed: "2026-02-16"
---

# Phase 16 Plan 02: Deploy Failure Issue Module Summary

**GitHub issue creation/append on deploy failure with deploy-failure, severity:high labels**

## Accomplishments
- failure_issues.py: create_or_append_deploy_failure_issue(gh_repo, sha, run_url, conclusion, failure_type)
- Labels: deploy-failure, severity:high, failure_type (e.g. deploy:health-check-failed, deploy:cancelled)
- Append path: same-SHA issue within 30 min window gets comment appended
- Returns issue number or None on error

## Task Commits
1. **Task 1: failure_issues.py** - `7d7e0fd` (feat)

## Deviations from Plan
None - plan executed as specified.

## Issues Encountered
None

---
*Phase: 16-deploy-integration-operator-ux*
*Completed: 2026-02-16*
