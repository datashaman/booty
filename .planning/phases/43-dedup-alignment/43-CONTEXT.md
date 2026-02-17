# Phase 43: Dedup Alignment - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Standardize dedup keys across queues and agents for correct multi-repo behavior. Add `repo_full_name` to VerifierQueue and SecurityQueue; document dedup keys for issue agents (Planner, Builder). No new capabilities — alignment and documentation only.

</domain>

<decisions>
## Implementation Decisions

### Issue agent dedup key design

- **Issue events:** `(repo, delivery_id)` — Planner and issue-driven Builder use this key
- **Plan-originated work:** `plan_hash` — Builder when triggered by Architect-approved plan uses `(repo, plan_hash)`
- **Builder:** Two keys — `(repo, delivery_id)` for issue-driven; `(repo, plan_hash)` for plan-driven. Document both now even though plan-driven wiring arrives in Phase 44
- **Architect:** Document "Architect: TBD in Phase 44" — reserve the slot and naming now

### Transition behavior

- **Rollout:** Single atomic change — update VerifierQueue and SecurityQueue signatures and all callers in one PR
- **In-flight jobs:** Ignore — in-memory queues; process restart clears state
- **Caller scope:** Audit and update router + any direct webhook handlers; all enqueue paths must pass repo
- **Missing repo:** Hard fail — new API requires repo; missing arg raises (no fallback)

### Claude's Discretion

- Exact key serialization (string vs tuple representation)
- Documentation placement and depth for the dedup key standard
- Whether to explicitly verify ReviewerQueue alignment (already correct per Phase 38)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 43-dedup-alignment*
*Context gathered: 2026-02-17*
