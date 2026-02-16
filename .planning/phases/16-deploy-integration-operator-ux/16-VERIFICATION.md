# Phase 16: Deploy Integration & Operator UX — Verification

**Status:** passed
**Date:** 2026-02-16

## Phase Goal

workflow_dispatch deploy, HOLD/ALLOW UX, post-deploy observation, failure issues.

## Must-Have Verification

### Plan 16-01: Deploy Trigger & HOLD/ALLOW UX
| Must-Have | Status | Evidence |
|-----------|--------|----------|
| On ALLOW: deploy workflow dispatches with sha input | ✓ | webhooks.py: dispatch_deploy(gh_repo, governor_config, head_sha) when decision.outcome == "ALLOW" |
| On ALLOW: commit status shows Triggered deploy workflow run | ✓ | ux.py post_allow_status description="Triggered: deploy workflow run" |
| On HOLD: commit status shows reason, SHA, how to unblock | ✓ | ux.py post_hold_status with reason-specific unblock text |
| Never deploys non-head_sha (GOV-18) | ✓ | head_sha from payload only; no "latest" |
| dispatch_deploy in deploy.py | ✓ | deploy.py provides function |
| post_hold_status, post_allow_status in ux.py | ✓ | ux.py provides both |
| webhooks → deploy.dispatch_deploy when ALLOW | ✓ | Line 359 |
| webhooks → ux.post_hold_status when HOLD | ✓ | Line 378 |

### Plan 16-02: Deploy Failure Issue Module
| Must-Have | Status | Evidence |
|-----------|--------|----------|
| On deploy failure: GitHub issue with deploy-failure, severity:high | ✓ | failure_issues.py labels=["deploy-failure","severity:high", failure_type] |
| Issue includes Actions run link | ✓ | Body includes run_url |
| Same SHA rapid retry: append to existing issue | ✓ | 30 min window, search open issues by deploy-failure, match title |
| create_or_append_deploy_failure_issue in failure_issues.py | ✓ | Module provides function |

### Plan 16-03: Deploy Outcome Observation
| Must-Have | Status | Evidence |
|-----------|--------|----------|
| Governor observes deploy workflow_run completion | ✓ | is_deploy branch in webhooks |
| On success: production_sha updated, deploy_history appended | ✓ | state.production_sha_*, append_deploy_to_history(success) |
| On failure: create_or_append_deploy_failure_issue called | ✓ | Line 307 in webhooks |
| Deploy workflow filtered by deploy_workflow_name | ✓ | path.endswith(deploy_workflow_name) or name == deploy_workflow_name |

## Summary

All must-haves verified against actual codebase. Phase goal achieved.
