# Phase 7: GitHub App + Checks Integration - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Unblock the Checks API — create `booty/verifier` check run using GitHub App auth. Settings extension, `checks.py`, GitHub App setup docs, and manual verification path. Phase 8 owns test parsing and rich failure diagnostics; Phase 7 delivers auth + plumbing.

</domain>

<decisions>
## Implementation Decisions

### Check run presentation

- **Name:** `booty/verifier` (exact) — matches required-check key; avoid name drift
- **Lifecycle:** Queued → In progress → Completed (success/failure) — establish lifecycle semantics immediately; users see it's alive
- **Output (informative):** Include in check output:
  - head SHA (short)
  - start/end timestamps + duration
  - mode: manual or agent
  - result: pass/fail
  - pointer: "details in PR comment" (later)
- **Phase 7 scope:** Prove check creation + full lifecycle; meaningful diagnostics deferred to Phase 8

### Optional-config feedback

- **Startup when disabled:** Explicit log — "Verifier: disabled (missing GITHUB_APP_ID or GITHUB_APP_PRIVATE_KEY)"
- **Misconfiguration:** Log error and continue; include reason class: `auth_failed` / `bad_key` / `jwt_failed`
- **Runtime status:** `booty status` prints `verifier: enabled|disabled` and last auth error
- **Webhooks when disabled:** Accept events, return 2xx, no-op; log "Verifier disabled; skipping check run" — keeps webhook plumbing stable; enable later without reconfiguring GitHub

### GitHub App setup docs

- **Location:** Both — README short blurb + link; detailed doc at `docs/github-app-setup.md`
- **Audience:** Both — separate sections: "Create a new App" and "Use an existing App"
- **Depth:** Step-by-step checklist style; copy/paste values; explicit UI paths
- **Not configured:** "If not configured" section — Verifier disabled, webhooks no-op, confirm via `booty status`

### Manual verification path

- **CLI:** `booty verifier check-test --repo owner/repo --sha <head_sha>` — permanent operator primitive
- **Requirements:** Env vars + repo/sha args; fail if repo or sha missing — never guess targets
- **Optional flags:** `--installation-id`, `--details-url`, `--dry-run`
- **Documentation:** README → 3-line quick verify; `docs/github-app-setup.md` → full example + expected output + screenshot of the check
- **Command output (required):** Must print: `check_run_id`, `installation_id`, `repo`, `sha`, `status`, `url` — operators jump straight to the check from terminal output

### Claude's Discretion

- Exact log message wording (beyond specified phrases)
- PyGithub integration details for lifecycle transitions
- `booty status` output format (beyond verifier + last auth error)

</decisions>

<specifics>
## Specific Ideas

- "booty/verifier exact — matches required-check key; avoid name drift"
- "Informative output — enough context to debug without opening logs"
- "Treat check-test as operator primitive — rotating keys, debugging auth, validating installs, testing new repos"
- "Operators should be able to jump straight to the check from terminal output"
- docs/github-app-setup.md should include screenshot of the check in GitHub UI

</specifics>

<deferred>
## Deferred Ideas

- Meaningful diagnostics in check output (test failures, annotations) — Phase 8
- Rich failure slices — Phase 8
- None beyond phase boundary

</deferred>

---

*Phase: 07-github-app-checks*
*Context gathered: 2026-02-15*
