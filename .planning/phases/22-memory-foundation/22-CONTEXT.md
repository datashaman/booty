# Phase 22: Memory Foundation - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Storage, schema, config, add_record API, and dedup for the Memory Agent. Records persist to memory.jsonl; agents and downstream phases (ingestion, lookup, surfacing) consume this foundation. Clarifies how to implement what's scoped — no new capabilities.
</domain>

<decisions>
## Implementation Decisions

### Dedup semantics
- Keep first: later duplicates within the window are ignored (idempotent)
- Exclude null/empty from dedup key: don't dedup on missing fields (fingerprint, pr_number); only match on fields that are present
- API distinguishes: return `{ added: false, reason: "duplicate", existing_id: ... }` vs `{ added: true, id: ... }`
- 24h window anchored on the first record for that key (window starts when first write for that key occurs)

### Config: default state
- Memory enabled by default; opt out with `enabled: false`
- When disabled: `add_record` is a no-op (returns success, doesn't persist) — idempotent
- Strict layering: config file first, env overrides only the keys it explicitly sets
- When memory block exists but `enabled` is omitted: default to enabled

### Unknown-key handling
- Fail config load for Memory only (agents can't use memory when unknown keys present)
- Clear error message with unknown key name and file location
- Future-proofing: any key not in the known list is unknown; typos are errors
- Parse together, fail separately: shared config parse; Memory-specific failure doesn't break other agents

### Retention / compaction
- Compact = archive: old records moved to separate file (e.g. `memory-archived.jsonl`), removed from main file
- Compaction runs periodically (background / scheduled)
- Batch compaction: threshold-triggered + periodic
- Partial last line during compaction: skip and delete

### Claude's Discretion
- Exact archive filename/pattern
- Compaction schedule/interval and threshold values
- Env variable naming for overrides (MEMORY_* per MEM-26)
</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for archive layout, compaction timing, and API shape.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 22-memory-foundation*
*Context gathered: 2026-02-16*
