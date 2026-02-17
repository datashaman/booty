# Phase 36: Builder Handoff & CLI - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Persist approved ArchitectPlan artifact, emit approval event, and have Builder consume from Architect. Add CLI commands for Architect status and force re-evaluation. Emit metrics and typed events for observability and future routing.

Scope: ARCH-26, ARCH-27, ARCH-28, ARCH-29, ARCH-30, ARCH-33.

</domain>

<decisions>
## Implementation Decisions

### Status command output
- Key-value lines (not table, not sectioned)
- Global summary by default; `--repo` or inferred cwd repo for drill-down
- `--json` flag for machine-readable output
- Breakdown for plans (24h): approved, rewritten, blocked — not a single aggregate count

### Review command behavior
- Repo: infer from git in cwd; optional `--repo OWNER/NAME` override; fail clearly if neither resolves
- On approve: summary output — goal (first line), step count, risk level, outcome
- On block: exit 1 with short message, e.g. "Architect blocked — see comment on issue #N"
- Non-interactive by default; suitable for CI; no prompts

### Builder trigger flow
- Hybrid: enqueue Builder in-process; emit structured event for metrics/traceability
- Webhook: if Architect-approved plan exists for the issue's current Planner input hash → enqueue Builder; else enqueue Planner (→ Architect → Builder)
- Builder consumption: artifact first (`~/.booty/state/plans/<repo>/<issue>-architect.json`); fall back to Planner plan for backward compatibility; mark PR as "unreviewed by Architect" when using fallback
- Typed events: `planner.plan.approved`, `architect.plan.approved`, `architect.plan.rewritten`, `architect.plan.blocked` for future routing and observability

### Metrics visibility
- Both: structured logs + metrics endpoint (Prometheus/OpenTelemetry-style)
- `booty architect status` includes breakdown: approved, rewritten, blocked, cache_hits
- Persisted under `~/.booty/state/architect/` — counters and small rolling window store so status survives restarts
- Rolling 24 hours from now (not calendar day)

### Claude's Discretion
- Exact key-value formatting and field names for status output
- Metrics endpoint wiring (if not already in codebase)
- Event payload structure for typed events
- Path structure within `~/.booty/state/architect/` for rolling window

</decisions>

<specifics>
## Specific Ideas

- Status: "plans reviewed (24h)" shows approved / rewritten / blocked breakdown
- Review: "Enough signal without dumping the plan"
- Blocking is a gating failure — exit code must reflect that
- Webhook must match approved plan to current Planner input hash (avoid stale approval)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 36-builder-handoff-cli*
*Context gathered: 2026-02-17*
