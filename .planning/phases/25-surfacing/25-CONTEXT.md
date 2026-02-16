# Phase 25: Surfacing - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Surface memory context at three integration points: Builder PR comment, Governor HOLD details, and Observability incident issue body. All informational only; no outcomes blocked or altered. MEM-19 to MEM-23.

</domain>

<decisions>
## Implementation Decisions

### PR comment: trigger timing
- **Trigger:** When Verifier check run completes (not on every pull_request event)
- **Scope:** PR opened + synchronize — Memory surfaces on both, but only after Verifier has run on that commit
- **Owner:** Memory has its own webhook handler (e.g. on `check_run` when Verifier completes), not piggybacking on Verifier code
- **PR filter:** All PRs when Memory is enabled; no agent-specific filter
- **Comment:** Single updatable comment (marker `<!-- booty-memory -->`); find-or-edit pattern like Verifier

### Governor HOLD: where memory links go
- **Surface:** Same PR comment as Builder PR — one updatable Memory comment per PR
- **When:** Governor HOLD fires → find PR for the commit → if PR exists and `comment_on_pr` enabled, update comment with 1–2 hold-reason matches
- **No PR:** Try to find PR for commit; if none, skip (no separate surface)
- **Lookup:** All HOLD reasons; fingerprint (reason) filters to relevant matches
- **Config:** Reuse `comment_on_pr` — Governor only surfaces when it can add to a PR comment

### Observability: Related history placement and format
- **Placement:** After Sentry link, before stack trace — operators see incident basics and related history before deep stack
- **Format:** Longer than PR — include severity or extra context for triage
- **Path source:** Use both stack frames and fingerprint; lookup may return fewer path matches
- **Config:** When `comment_on_incident_issue` false — skip lookup entirely (do not query memory)

### Empty state: zero matches
- **PR comment:** Omit entirely — no Memory comment when zero matches
- **Governor:** Only add Governor section when there are matches; if zero, don't add section
- **Observability:** Omit "Related history" section entirely when zero matches
- **Consistency:** Surfaces can differ; no requirement for uniform empty handling

### Claude's Discretion
- Exact PR comment format (per-match layout: type, date, summary, link)
- Exact Observability section format (severity/context fields)
- How to derive paths from Sentry stack frames for lookup
- Webhook routing details (check_run vs workflow_run for Verifier completion)
- How to find PR for a commit when Governor holds

</decisions>

<specifics>
## Specific Ideas

No specific references — decisions above provide concrete guidance. Follow existing patterns: `post_verifier_failure_comment` for find-or-edit comment; `build_sentry_issue_body` for issue body structure.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 25-surfacing*
*Context gathered: 2026-02-16*
