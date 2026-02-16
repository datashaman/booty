# Phase 15: Trigger, Risk & Decision Logic - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

workflow_run handler, risk scoring from paths, decision rules, cooldown and rate limit. Governor receives verification workflow completion on main, computes risk from diff vs production_sha, applies hard holds and approval policies, and enforces cooldown/max_deploys_per_hour. Deploy integration (workflow_dispatch, HOLD/ALLOW UX) is Phase 16.

</domain>

<decisions>
## Implementation Decisions

### Degraded / incident signal behavior
- Unknown degraded: hold HIGH only; MEDIUM and LOW allowed
- Degraded + MEDIUM risk: hold (same as HIGH when degraded)
- Degraded + LOW risk: allow — LOW always auto-ALLOWs regardless of degraded
- Degraded signal source: in-process for now; Sentry integration deferred

### Approval channel mechanics (HIGH risk)
- Env var: per-run — passed into Governor when it runs (e.g., from manual workflow run)
- Label: specific label (e.g. `release:approved`) on the PR that was merged
- Comment: comment on the PR that was merged to main
- Channels: OR — any one of env, label, or comment counts as approval

### First-deploy approval semantics
- "First deploy" = per environment (future-safe for staging vs production)
- Configurable: `require_first_deploy_approval: true|false` in .booty.yml
- Approval channels: same as HIGH risk (env, label, comment)
- HOLD UX: special reason text that explains how to approve (env/label/comment)

### Risk classification edge cases
- Multi-category match (e.g. manifest + infra dir): take highest risk
- Unlisted file types: default to LOW
- Pathspec format: both directory prefixes and glob patterns supported
- Empty diff: treat as LOW — allow (Verifier passed, nothing risky)

### Claude's Discretion
- Exact degraded signal integration (in-process store shape, API)
- Exact approval label name and comment format
- Pathspec config structure (separate HIGH/MEDIUM lists vs unified)
- Cooldown and rate-limit storage details

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

- Sentry-based degraded signal — future phase
- Staging vs production deploy targets — future phase

</deferred>

---

*Phase: 15-trigger-risk-decision-logic*
*Context gathered: 2026-02-16*
