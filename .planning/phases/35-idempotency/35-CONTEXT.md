# Phase 35: Idempotency - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

plan_hash cache; reuse ArchitectPlan within configurable TTL when plan unchanged. Same plan (by hash) approved or blocked within TTL reuses prior outcome; no re-validation. Update comment only if booty-architect block differs. This phase covers cache identity, TTL semantics, comment update policy, and blocked-plan handling — not persistence artifact path or handoff (Phase 36).

</domain>

<decisions>
## Implementation Decisions

### Hash input scope
- plan_hash = sha256(plan_json) over **normalized form**, not raw Planner output
- Exclude volatile metadata — follow Planner (Phase 31) exclusions (e.g. created_at and fields that change per run)
- Deterministic JSON for hashing: sorted keys, canonical serialization (no insignificant whitespace, UTF-8, stable list ordering)

### 24h window semantics
- Same as Planner: timestamp source = `created_at` stored in plan metadata; TTL runs from that timestamp
- Configurable via `ARCHITECT_CACHE_TTL_HOURS` (env); default 24
- Strict expiry — expired = cache miss; no grace period
- UTC only

### Comment update on cache hit
- Diff first — compute booty-architect block we'd post, compare to existing block; update only if different
- No cache indication in comment — same as Planner; cache is implementation detail
- Missing or modified booty-architect block = changed → rewrite to canonical cached output
- No existing block → insert it from cached ArchitectPlan

### Blocked-plan handling
- Cache block outcome — same plan blocked within TTL short-circuits
- Short-circuit: immediately re-block with prior reason; no re-validation
- Same TTL as approvals
- Block comment update: same as approval — diff first; update only if block differs

### Claude's Discretion
- Exact fields to exclude from hash (align with Phase 31 pattern)
- Cache storage layout and lookup key structure
- Diff comparison strategy (exact string, normalized comparison, etc.)

</decisions>

<specifics>
## Specific Ideas

- Align with Phase 31 patterns where applicable (TTL, UTC, cache as implementation detail)
- Avoid comment churn — diff before update

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 35-idempotency*
*Context gathered: 2026-02-17*
