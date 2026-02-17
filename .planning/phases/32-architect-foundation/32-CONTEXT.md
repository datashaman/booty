# Phase 32: Architect Foundation - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Architect config in .booty.yml, triggering from Planner completion (not GitHub labels), and input ingestion (plan_json, normalized_input, optional repo_context, optional issue_metadata). Architect sits between Planner and Builder — Planner completion → Architect → Builder. This phase establishes the plumbing: config schema, when Architect runs, what it receives, and how failures are handled.

</domain>

<decisions>
## Implementation Decisions

### Config block semantics
- **enabled=false:** Pass plan straight through — Planner → Builder directly (Architect skipped; same as current flow)
- **Defaults:** rewrite_ambiguous_steps and enforce_risk_rules both default to true (strict by default)
- **Env overrides:** Only ARCHITECT_ENABLED as a kill switch (no other env overrides for architect block)
- **Missing architect block:** Architect enabled with defaults

### Triggering behavior
- Architect runs only when plan changes (new generation); Planner cache hit → skip Architect
- Architect runs synchronously in the same flow as Planner completion; then enqueue Builder when approved
- Debounce Architect runs per issue within a time window (coalesce rapid successive triggers)
- On Planner failure: Architect never runs; no Builder

### Degraded operation (missing repo_context)
- **Validation:** Full validation except risk recomputation — risk left as-is from Planner when repo_context is missing
- **User-facing note:** Add architect_notes: "Evaluated without repo context" when repo_context was missing
- **When repo_context is missing:** No token, missing owner/repo, or token/API errors
- **Empty/sparse touch_paths:** Validate what's present; empty paths still flagged per ARCH-10 (no relaxation)

### Unknown key failure
- Unknown keys in architect block (including typos like "enabeled"): Architect run aborts, do not enqueue Builder
- Post comment: "Architect review required — invalid architect config in .booty.yml"
- Detect at config load before Architect runs — validate architect block, fail fast
- Invalid config blocks Builder completely; operator must fix .booty.yml

### Claude's Discretion
- Debounce time window duration
- Exact comment phrasing for invalid config (can refine from the stated message)
- Config validation error message details

</decisions>

<specifics>
## Specific Ideas

- Follow existing config block patterns (Security, Governor, Planner) for ArchitectConfig schema
- "Architect only" failure scope — Planner and webhook unaffected when architect config fails

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 32-architect-foundation*
*Context gathered: 2026-02-17*
