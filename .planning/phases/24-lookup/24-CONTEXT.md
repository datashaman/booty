# Phase 24: Lookup - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Deterministic query engine that accepts a candidate change (paths, repo, head sha) and returns related memory records from the last 90 days. Matching by path intersection OR fingerprint; no embeddings; fast (<1s for 10k records). MEM-15 to MEM-18.

</domain>

<decisions>
## Implementation Decisions

### Path matching rules
- **Match semantics:** Prefix/containment — record path is prefix of candidate OR candidate is prefix of record path
- **Direction:** Record path as prefix of candidate counts (e.g. `src/foo` matches `src/foo/newfile.ts`)
- **Path overlap count:** Weighted — exact match = 2, prefix match = 1
- **Normalization:** Normalize paths before comparison (slashes, `./` handling)

### Fingerprint in the query
- **Caller-specific:** Builder PR uses paths only; Governor (and optionally Verifier) may pass fingerprint
- **Governor:** Passes reason as fingerprint → match records with same reason
- **Verifier-style:** Use both — path intersection finds records; derive paths_hash from candidate paths to match verifier_cluster fingerprints when caller has paths
- **Logic:** Additive — include records that match by path OR by fingerprint

### Result limits and API shape
- **Limits:** Lookup has built-in cap from config (max_matches); callers can override via API param (e.g. max=10 for CLI)
- **Fields per match:** Subset — type, date, summary, link, id (for dedup); only what Surfacing needs
- **"Up to 3" for PR comment:** Lookup enforces; Surfacing calls with max from config
- **CLI:** `--limit N` flag; default uses config (or larger for debugging)

### Severity and tie-breaking
- **Canonical scale:** Fixed — critical > high > medium > low > unknown
- **Missing severity:** Treat as lowest (unknown), sort last
- **Final tie-breaker:** Record id (string sort) when severity, recency, path_overlap all equal
- **Recency:** Based on event timestamp (record.timestamp, set from event at ingestion)

### Claude's Discretion
- Exact path normalization algorithm (e.g. handling Windows vs Unix, trailing slashes)
- Severity mapping from source-specific values (Sentry level, risk_class, etc.) to canonical scale
- API signature details (param names, return type structure)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Decisions above provide concrete guidance for lookup behavior.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 24-lookup*
*Context gathered: 2026-02-16*
