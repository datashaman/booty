# Phase 47: Operator Visibility - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Operator visibility: structured skip logs when events are ignored, and `booty status` CLI showing enabled agents, last run timestamps, and queue depth. OPS-01 through OPS-04. Verifier `promotion_waiting_reviewer` already exists; verify and document.

</domain>

<decisions>
## Implementation Decisions

### Skip log volume
- Log router skips only in Phase 47 (not worker-level skips).
- INFO for operator-actionable skips: `disabled`, `missing_config`, `normalize_failed`.
- DEBUG for high-volume skips: `not_agent_pr`, `dedup_hit`, and "expected routing misses" (e.g. no trigger label).
- No batching or summarizing in Phase 47.

### booty status layout and content
- Keep key/value style per agent.
- Add two fields per agent:
  - `last_run_completed_at` — ISO-8601 UTC, last completed run (success/failure/cancelled); not queued time.
  - `queue_depth` — integer when available; otherwise N/A.
- If a field is unknown, print N/A (don't omit).

### Skip reason vocabulary
- Public vocabulary: OPS-02 four + one extra — `disabled`, `not_agent_pr`, `missing_config`, `dedup_hit`, `normalize_failed`.
- Map all other router reasons into these five buckets.
- Keep original granular reason in a debug-only field.

### Agent coverage in booty status
- Add Builder and Reviewer to the status output.
- Show `last_run_completed_at` and `queue_depth` for them; use N/A fallback when data isn't available yet.

### Claude's Discretion
- Exact mapping of router reasons to the five buckets.
- Where to source last_run_completed_at (which stores, metrics).
- Queue depth instrumentation approach when not yet available.

</decisions>

<specifics>
## Specific Ideas

- No specific references — decisions captured above.
- Timestamp format: ISO-8601 UTC.

</specifics>

<deferred>
## Deferred Ideas

- Worker-level skip logging — Phase 47 is router-only.
- Log batching/summarizing — not in scope.
- OPS-05 (persistent queue metrics) — future phase per REQUIREMENTS.md.

</deferred>

---

*Phase: 47-operator-visibility*
*Context gathered: 2026-02-17*
