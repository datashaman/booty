---
phase: 42-event-router
status: passed
verified: 2026-02-17
---

# Phase 42: Event Router — Verification

**Status:** passed

## Must-Haves Check (against codebase)

### Plan 01 — Events + Normalizer
- [x] IssueEvent, PREvent, WorkflowRunEvent carry action, routing fields, raw_payload
- [x] normalizer converts GitHub payloads to internal events before routing
- [x] Router events observable (event_skip structured logging)
- [x] events.py ≥60 lines (60)
- [x] normalizer.py ≥80 lines (169)
- [x] normalize_* return IssueEvent|PREvent|WorkflowRunEvent

### Plan 02 — should_run
- [x] should_run(agent, repo, context) single decision point
- [x] Precedence: env > file > default
- [x] enabled(agent) and should_run(agent, ctx) two layers
- [x] should_run.py ≥80 lines (108)
- [x] Links to booty.config (planner_enabled, verifier_enabled, etc.)

### Plan 03 — Router + Webhook Wire
- [x] Webhook calls router as single dispatch
- [x] issues.labeled/opened → planner|builder (ROUTE-02)
- [x] pull_request → reviewer|verifier|security (ROUTE-03)
- [x] workflow_run → governor.evaluate|observe_deploy (ROUTE-04)
- [x] All enqueue paths use should_run (ROUTE-05)
- [x] router.py ≥120 lines (616)
- [x] webhooks.py delegates via route_github_event()

## Phase Goal

**Single canonical event router** — ROUTE-01 through ROUTE-05 complete.

- Normalization layer extracted
- should_run single decision point with config+env precedence
- Webhook delegates issues, pull_request, workflow_run to router
- check_run, push, sentry remain in webhooks (side-channels)
