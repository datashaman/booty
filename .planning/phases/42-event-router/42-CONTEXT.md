# Phase 42: Event Router - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Single canonical event router that normalizes GitHub webhook events into internal events before enqueue. Maps issues.labeled/opened → planner|builder, pull_request → reviewer|verifier|security, workflow_run → governor. Single should_run decision point with config+env precedence governs all enqueue decisions. ROUTE-01 through ROUTE-05.

</domain>

<decisions>
## Implementation Decisions

### Internal event shape
- **Event-type-specific structs with raw payload** — Typed per event family (IssueEvent, PREvent, WorkflowRunEvent); each keeps `raw_payload` for agent-specific parsing. Structs give stable, typed routing fields; raw payload preserves flexibility.
- **Extract for routing + minimal shared context** — Routing fields + minimal shared: `action`, `issue_number`/`pr_number`, `head_sha`, `workflow_run` id/name/conclusion, `sender`, `delivery_id`. Agents read `payload` for specifics; keeps agents independent.
- **Dedup keys computed by router at route time** — Router derives and passes dedup keys when enqueueing. Router-owned dedup is the only place that can enforce cross-agent consistency and prevent double-enqueue before jobs exist.
- **Incremental migration** — Internal events used for routing and dedup first; keep current job payload shapes initially. Avoids rewriting every job constructor; enqueue paths can be flipped one-by-one without breaking agents.

### should_run precedence
- **Precedence order:** Env overrides file; file over default; explicit env wins over implicit. Operator control plane = env; repo config = repo policy; defaults = fallback.
- **Global kill switch + per-agent** — Global kill switch required for incident response; per-agent remains the normal control surface.
- **Two layers:** `enabled(agent)` for enablement; `should_run(agent, ctx)` for routing/gating. Both feed the final decision. Separates enablement from routing/gating; prevents circular dependency (Builder enablement shouldn't depend on Architect state); gating stays in flow controller.
- **Per-agent policy for missing config** — Defaults differ by agent role: Planner/Builder are workflow drivers; Verifier/Security are safety rails; Architect/Reviewer are optional gates. Per-agent defaults keep this coherent (e.g. Reviewer disabled by default when block missing; Planner enabled by default).

### Claude's Discretion
- Operator observability (ROUTE-01 "observe") — logs, structure, or endpoint
- Filtered event handling — whether Phase 42 adds minimal skip observability or defers to Phase 47 (OPS-01)
- Exact per-agent default values when file absent
- Global kill switch env var naming and semantics

</decisions>

<specifics>
## Specific Ideas

- "Router-owned dedup is the only place that can enforce cross-agent consistency"
- "Incremental migration — flip enqueue paths one-by-one without breaking agents"
- "enablement vs routing/gating — prevents circular dependency"
- Per-agent role framing: drivers (Planner/Builder), safety rails (Verifier/Security), optional gates (Architect/Reviewer)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 42-event-router*
*Context gathered: 2026-02-17*
