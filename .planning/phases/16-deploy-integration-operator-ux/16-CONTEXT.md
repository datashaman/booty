# Phase 16: Deploy Integration & Operator UX - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

workflow_dispatch deploy trigger, HOLD/ALLOW operator UX, post-deploy observation, and deploy failure issue handling. Governor triggers deploy on ALLOW, surfaces HOLD/ALLOW to operators, observes deploy workflow completion, updates release state, and creates/updates GitHub issues on deploy failure. Never deploys non-head_sha (GOV-18).

</domain>

<decisions>
## Implementation Decisions

### Operator feedback surface (GOV-25)
- Use **commit status** (`booty/release-governor`), not issue comment
- Attach to **merge commit on main** (the commit that triggered verification)
- Status indicates state only; full details live elsewhere (target URL)
- Create GitHub issues **only for deploy failures** (GOV-17) — not for pre-deploy HOLDs

### "How to unblock" content (GOV-23)
- **Reason-specific** instructions — different text for first-deploy vs high-risk vs degraded, etc.
- **Config-driven** for approval — reflect `approval_mode` from config (e.g. "Approval via label: release:approved")
- **Include SHA** in first-deploy HOLD (e.g. "First deploy for abc123 — add approval then retry")
- Status **target_url** links to a page containing full "how to unblock" — planner decides best target

### Deploy failure issue strategy (GOV-17)
- **Hybrid:** new issue per SHA; append to that issue if same SHA fails again
- **Severity/mode:** create new issue for first failure after long quiet period; append for rapid retries (planner defines thresholds)
- **Labels:** include failure type (e.g. `deploy:health-check-failed`) in addition to `deploy-failure`, `severity:high`
- Failure issues are **visibility only** — no coupling to Governor decision logic; cooldown/rate-limit stay separate

### Deploy outcome observation (GOV-16)
- **workflow_run** only — no deployment_status / Deployments API
- **Webhook preferred** — receive workflow_run events; fallback to polling if needed
- **workflow_run conclusion** defines deploy completion (success, failure, cancelled)
- **Periodic reconciliation** — check recent workflow runs to align release state when events may have been missed

### Claude's Discretion
- Exact target URL for "how to unblock" details (Actions run vs docs vs other)
- Failure issue append vs new thresholds (time window, retry cadence)
- Polling fallback trigger conditions and frequency
- Reconciliation cadence and scope

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 16-deploy-integration-operator-ux*
*Context gathered: 2026-02-16*
