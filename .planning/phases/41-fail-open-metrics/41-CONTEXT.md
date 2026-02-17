# Phase 41: Fail-Open + Metrics - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Harden Reviewer failure handling (fail-open when infra/LLM fails), emit metrics and structured logs, add minimal docs. REV-09, REV-15. No new capabilities — implementation choices only.
</domain>

<decisions>
## Implementation Decisions

### Fail-open user visibility
- Check output only — no PR comment when fail-open triggers
- Title must say "Reviewer unavailable (fail-open)"
- Summary must explicitly say "Review did not run; promotion/merge not blocked" — no "approved" wording

### Fail-open trigger scope
- Distinguish types for metrics/logs, but keep user-facing check text generic
- Bucket failures as: diff_fetch_failed, github_api_failed, llm_timeout, llm_error, schema_parse_failed, unexpected_exception

### Metrics storage and consumption
- Same pattern as Architect: persisted rolling-window counters under `~/.booty/state/reviewer/metrics.json`
- `booty reviewer status` with `--json` option
- Do not depend on log aggregation for status (metrics must be persisted)

### Docs depth
- reviewer.md includes: enable/disable config, block_on semantics, fail-open semantics (what triggers, what users see), emitted metrics names, troubleshooting checklist (token missing, diff fetch, LLM timeout)
- No tutorials

</decisions>

<specifics>
## Specific Ideas

- Fail-open buckets: diff_fetch_failed, github_api_failed, llm_timeout, llm_error, schema_parse_failed, unexpected_exception
- Status command must read from persisted metrics, not logs
- Troubleshooting checklist: token missing, diff fetch, LLM timeout

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 41-fail-open-metrics*
*Context gathered: 2026-02-17*
