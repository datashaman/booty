# Phase 31: Idempotency - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Same plan for unchanged inputs within configurable TTL. Check for cached plan before LLM call; return cached when inputs match. Plan metadata includes plan_hash (hash of normalized plan) for dedup. Output is reproducible for unchanged inputs. Scope is fixed — implementation clarifies HOW to implement this behavior.

</domain>

<decisions>
## Implementation Decisions

### Input comparison scope
- Compare: goal + body + labels + source_type + incident_fields
- Include default_branch from repo_context; exclude tree
- Canonical form for comparison (normalized whitespace, sorted labels)
- Cache key: issue identity (owner, repo, number) + input hash — separate cache per issue
- metadata (repo, issue_url, issue_number) excluded from comparison

### 24h window semantics
- Sliding window with configurable duration (e.g. env `PLANNER_CACHE_TTL_HOURS`, default 24)
- UTC only
- Timestamp source: `created_at` stored in plan metadata
- Use until exactly TTL; no grace period

### Ad-hoc (CLI) idempotency
- Separate cache from issue cache — qualitatively different lifecycle
- Lookup key: hash of canonical input + optional repo context when provided
- Keep timestamped paths (`ad-hoc-<ts>-<hash>.json`); lookup via hash index — preserves history, no overwrite
- Directory/cwd not part of key — same text from different dirs → same cached plan

### Cache hit behavior — GitHub
- Update existing comment when cache hit ( locate via marker; replace content)
- No new comment; no "cache hit" indication in issue — cache is implementation detail

### Cache hit behavior — CLI
- Same formatted output plus line "(cached, created at …)" for temporal awareness
- Write to same cached path — no duplicate artifacts, preserves determinism

### plan_hash
- Plan metadata includes plan_hash (hash of normalized plan) for dedup and reproducibility
- Hash excludes metadata fields that change per run (e.g. created_at)

### Claude's Discretion
- Exact canonical form specification (whitespace rules, label sort order)
- Hash index structure for ad-hoc lookup
- Marker/strategy for locating existing plan comment to update
- plan_hash input scope (which plan fields included)

</decisions>

<specifics>
## Specific Ideas

- "Preserves history + debuggability; do not overwrite artifacts" (ad-hoc storage)
- "Directory is an execution detail, not a planning input" (ad-hoc key)
- "Cache is an implementation detail; avoid comment churn" (GitHub UX)
- "Operators benefit from temporal awareness" (CLI cached hint)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 31-idempotency*
*Context gathered: 2026-02-16*
