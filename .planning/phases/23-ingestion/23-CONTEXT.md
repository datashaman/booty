# Phase 23: Ingestion - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire adapters from Observability, Governor, Security, Verifier, and Revert into Memory. Each source produces the appropriate record type (incident, governor_hold, deploy_failure, security_block, verifier_cluster, revert) and stores via memory.add_record. MEM-06 to MEM-12.

</domain>

<decisions>
## Implementation Decisions

### Revert detection (MEM-12)
- **Source:** Both automatic discovery and explicit input
- **Detection:** Either git message ("Revert ..." / "revert <sha>") or GitHub revert merge metadata; accept whichever is available
- **Scope:** Main branch only — only reverts that land on main (deployed line)
- **Explicit input:** CLI for manual use (`booty memory ingest revert`); Builder agent when it creates/applies a revert

### Security ESCALATE vs FAIL (MEM-09, MEM-10)
- **Distinguishability:** Use distinct fingerprint/reason in records — lookup can differentiate
- **Surfacing:** ESCALATE shows as "permission surface change"; FAIL as "blocking issue" (Phase 25)
- **Dedup:** Separate — same PR can produce one ESCALATE and one FAIL; both stored
- **Trigger tagging:** Always record `metadata.trigger`: "secret" | "vulnerability" | "permission_drift"

### Verifier cluster granularity (MEM-11)
- **Granularity:** One record per failure class (import, compile, test)
- **Combined failures:** Multiple records — e.g. import + compile = two records
- **Fingerprint:** `<failure_type>:<paths_hash>`
- **Test failures / dedup:** Dedup by (repo, pr, sha) — one record per SHA; subsequent identical SHA failures are duplicates

### Deploy failure scope (MEM-08)
- **Store:** Both failure and cancelled, tagged — `metadata.conclusion` distinguishes
- **Surfacing:** Exclude cancelled from "related history" lookup results (Phase 25)
- **Failure type:** Keep `deploy:health-check-failed`, `deploy:cancelled`; store in `metadata.failure_type`
- **Multiple runs:** Separate records — same SHA failing then cancelled = two records

### Claude's Discretion
- Exact fingerprint algorithm for paths_hash
- Spooled Observability events (retry path) — ingest on successful issue creation
- Builder agent integration point for explicit revert input

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Decisions above provide concrete guidance for each adapter.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 23-ingestion*
*Context gathered: 2026-02-16*
