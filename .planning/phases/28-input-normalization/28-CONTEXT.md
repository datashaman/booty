# Phase 28: Input Normalization - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Normalize three input sources (GitHub issue, Observability incident, CLI text) into a single Planner input context. The normalized structure feeds Phase 29's plan generation. Extraction, detection, and optional repo context are in scope. Plan generation and output delivery are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Normalized Structure Shape

- **Hybrid:** Flat `goal` + `body`, plus optional incident-specific sections when source is Observability (e.g. `location`, `sentry_url`)
- **Labels:** Pass all labels through; derive `source_type` (e.g. `incident`, `feature_request`, `bug`, `unknown`)
- **Metadata:** Rich — include repo info (owner, repo), `issue_url`, `issue_number` when present
- **Incident fields:** Minimal extraction — extract `location`, `sentry_url` (and similar key fields); rest stays in body

### Observability Incident Detection

- **Strategy:** Label primary (e.g. `agent:incident`), heuristics fallback (body markers like `**Severity:**`, `**Sentry:**`, title `[severity]`)
- **No repo:** Treat as incident anyway — apply incident extraction
- **Uncertain:** Treat as plain GitHub issue — default to normal handling
- **Scope:** Sentry-specific — only detect current Sentry format; don't over-engineer for future Observability sources

### Extraction Depth and Labels

- **GitHub issue body:** Pass full body with a length cap (trim only; no section extraction)
- **Incident body:** Keep full Sentry markdown as-is; extracted fields (location, sentry_url) are additive, not replacements
- **source_type:** Known set — `incident`, `feature_request`, `bug`, `unknown` (derive from labels or heuristics)
- **CLI --text:** Split into goal (first part) + body (remainder)

### Optional Repo Context

- **What to fetch:** Default branch + file tree (no recent commits for v1)
- **Tree depth:** Shallow — 2–3 levels from root
- **Recent commits:** Configurable when added later (default 5)
- **CLI without --repo:** Infer repo from cwd when in a git repo; omit repo context otherwise

### Claude's Discretion

- Exact trim length cap for body (balance context size vs completeness)
- Exact goal/body split for CLI text (first line vs first sentence vs first paragraph)
- Heuristic rules for deriving `source_type` from labels (e.g. `bug` label → `bug`, `enhancement` → `feature_request`)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Sentry issue format is defined in Phase 13 (Observability Agent); use `build_sentry_issue_body` output structure as reference for detection heuristics.

</specifics>

<deferred>
## Deferred Ideas

- Recent commits in repo context — configurable default 5 when added; defer to future iteration if needed
- Non-Sentry Observability sources — detection is Sentry-specific; extend format-agnostic detection in a later phase

</deferred>

---

*Phase: 28-input-normalization*
*Context gathered: 2026-02-16*
