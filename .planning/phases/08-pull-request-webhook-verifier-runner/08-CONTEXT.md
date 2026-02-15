# Phase 8: pull_request Webhook + Verifier Runner - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Verifier runs on every PR via pull_request webhook (opened, synchronize, reopened). Clones PR head in clean env, runs tests, posts booty/verifier check. Only agent PRs are blocked on failure; non-agent PRs get informational checks. Builder never promotes agent PRs; Verifier promotes when it passes.

</domain>

<decisions>
## Implementation Decisions

### Agent PR detection
- **Detection:** Agent PR = has label `agent:builder` OR PR author has `user.type == "Bot"` (GitHub API)
- **Label source:** Builder adds `agent:builder` to PRs it creates (Phase 8 scope)
- **Non-agent PRs:** Run check on every PR for visibility; only agent PRs are blocked on failure (non-agent = informational)
- **Bot detection:** Use `user.type == "Bot"` from GitHub API

### Event handling & deduplication
- **Events:** Handle `opened`, `synchronize`, and `reopened`
- **Rapid pushes:** When new synchronize arrives, cancel any in-progress Verifier for that PR and enqueue new run
- **Cancel behavior:** Hard cancel — stop running process (clone, test run) and start new one
- **Deduplication:** PR-level dedup — one active job per PR+head_sha; duplicate deliveries for same commit ignored

### Failure diagnostics
- **Check output:** Minimal — pass/fail, SHA, duration, mode. Full diagnostics in PR comment.
- **When to comment:** Only when Verifier blocks (agent PR failures)
- **Comment behavior:** Update single "Verifier results" comment per PR (edit/replace, not append)
- **Comment content:** Truncated output (e.g. last ~50 lines) — enough to diagnose without huge comments

### Builder–Verifier promotion flow
- **Who promotes agent PRs:** Verifier only — Builder never promotes agent PRs
- **When Verifier promotes:** After run completes successfully, Verifier calls `promote_to_ready_for_review`
- **Agent PRs stay draft** until Verifier promotes — no race condition
- **Post-promotion failure:** N/A — we never promote before Verifier runs

### Claude's Discretion
- Exact truncation line count for PR comment
- Hard-cancel implementation (e.g. process group kill vs task cancellation)
- Job queue integration for VerifierJob vs Builder Job (separate queue vs same queue with routing)
- Comment placement (first comment vs sticky location)

</decisions>

<specifics>
## Specific Ideas

- Agent PR detection reuses TRIGGER_LABEL ("agent:builder") for consistency with Builder
- PR-level dedup by PR number + head_sha — avoids redundant runs for same commit
- Single Verifier comment per PR — avoid comment spam on rapid pushes

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-pull-request-webhook-verifier-runner*
*Context gathered: 2026-02-15*
