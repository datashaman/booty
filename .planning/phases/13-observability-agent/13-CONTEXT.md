# Phase 13: Observability Agent - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Sentry webhook → verify → filter (severity, dedup, cooldown) → create GitHub issue with agent:builder label. Alert-to-issue pipeline that feeds production errors back as actionable issues for Builder intake. Webhook ingestion, filtering rules, issue creation, and failure handling are in scope. OBSV-09 (multiple projects), OBSV-10 (persistent cooldown), OBSV-11 (metrics) are deferred.

</domain>

<decisions>
## Implementation Decisions

### Severity Filtering
- Configurable cutoff per deployment — env and/or .booty.yml
- Config: both env and .booty.yml; env overrides .booty.yml fallback
- Default when unset: error and above (fail-safe — don't miss real errors)
- Model: single min-severity threshold (e.g., error → error, fatal pass through)

### Cooldown and Dedup
- Default cooldown: 6 hours — short enough to surface ongoing incidents, long enough to prevent alert storms
- Same fingerprint after cooldown expires: reuse existing issue, append comment — maintain incident continuity; new issues fragment operator context
- Correlation required: track fingerprint → GitHub issue ID to enable comment append
- Persistent cooldown: prefer if trivial; otherwise in-memory is fine — do not delay Observability for storage engineering (OBSV-10 deferred)
- Config: both env and .booty.yml; env overrides

### Issue Content and Format

**Title pattern:**
- `[severity] ExceptionType — path/to/file.py:line`
- Rules: lead with severity; include exception type; anchor to file:line when available; never include full message (too volatile → breaks dedup)

**Body order:**
1. Severity / environment / release
2. First seen / last seen
3. Sentry link
4. Location (file:line)
5. Top 7 frames
6. Breadcrumb excerpt

Operators should understand impact before clicking out. Full traces belong in Sentry. Goal: triage in <30 seconds.

**Breadcrumbs:**
- Last 8 breadcrumbs; truncate at 160 chars each
- Drop debug-level crumbs; keep errors + warnings preferentially
- Strip obvious secrets / tokens
- Breadcrumbs are hints, not logs

**Stack trace:**
- Top 7 frames only — large traces destroy scannability

### Failure and Edge Handling

**Webhook verification fails (bad/missing HMAC):**
- 401 with minimal body: `{"error":"invalid_signature"}`
- Do not leak validation detail

**HMAC secret missing at startup:**
- Fail startup — no secret = no server
- Unverified webhook is a remote code path into the issue system
- Do not special-case dev — use a dummy secret locally

**GitHub issue creation fails:**
- Observability events are production signals, not best-effort telemetry
- Retry: 3 attempts, exponential backoff (2s, 8s, 30s)
- Then → durable queue/spool — do not drop incidents; silent outages are unacceptable
- If proper queue not trivial: implement tiny disk spool (JSONL file acceptable for v1)

**Malformed or invalid payload (missing fingerprint, level, etc.):**
- 422 Unprocessable Entity — syntactically valid HTTP, semantically invalid
- Structured body: `{"error": "invalid_payload", "missing": ["fingerprint", "level"]}`
- Correct status matters for sender retry behavior

### Claude's Discretion
- Exact env var names (SENTRY_WEBHOOK_*)
- .booty.yml schema extensions for observability config
- Fingerprint → issue ID storage mechanism (when reusing issues)
- Disk spool format and location for failed GitHub API calls

</decisions>

<specifics>
## Specific Ideas

- "If you drop incidents, you create silent outages"
- Title never includes full message — volatile, breaks dedup
- Use dummy secret locally; no dev exception for unverified webhooks

</specifics>

<deferred>
## Deferred Ideas

- OBSV-09: Multiple Sentry projects or environments with routing rules
- OBSV-10: Persistent cooldown store (Redis) survives restarts
- OBSV-11: Observability agent metrics (webhooks received, issues created)

</deferred>

---

*Phase: 13-observability-agent*
*Context gathered: 2026-02-15*
