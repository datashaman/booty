# Phase 12: Sentry APM - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate Sentry SDK for error tracking in the Booty FastAPI app. Set release (git SHA) and environment for deploy correlation so events in Sentry can be tied to specific deploys. Capture unhandled exceptions and critical handled failures. Phase 13 (Observability Agent) handles Sentry webhooks and issue creation — out of scope here.

</domain>

<decisions>
## Implementation Decisions

### Release / SHA Source
- Deploy sets release via env var — deterministic, works without .git, aligns with immutable-release semantics
- Env var: `SENTRY_RELEASE` — direct mapping to Sentry
- When SHA unknown (local dev): **skip release** — do not set it; placeholders pollute Sentry grouping and dashboards
- Deploy writes `/etc/<service>/release.env` containing `SENTRY_RELEASE=<sha>`
- Systemd unit: `EnvironmentFile=/etc/<service>/release.env`
- Deploy runs `git rev-parse HEAD` before restart and writes to release.env

### Environment Tagging
- Configurable via env var — dev, staging, production
- Env var: `SENTRY_ENVIRONMENT`
- When missing: default to `"development"` so local events are clearly separated
- Deploy sets it in the same systemd release.env file (`SENTRY_RELEASE` + `SENTRY_ENVIRONMENT`)

### Missing DSN Behavior
- **Production + no DSN** → fail startup (misconfigured system; refuse to run blind)
- **Non-production + no DSN** → skip Sentry init, app runs normally
- Log once at startup when skipping: `Sentry disabled — no DSN configured (environment=development)` — do not log repeatedly
- DSN lives in **separate secrets file**: `/etc/<service>/secrets.env` — NOT in .env, NOT in release.env
- Systemd: `EnvironmentFile=/etc/<service>/secrets.env` (in addition to release.env)
- Secrets file is managed separately (manual or secrets management); deploy does not write to it

### Capture Scope
- Errors + breadcrumbs — unhandled exceptions plus breadcrumbs for context (request, DB, LLM activity)
- Error sample rate: configurable via `SENTRY_SAMPLE_RATE` env var, default 1.0
- Performance tracing: **skip** — `traces_sample_rate=0`; errors only this phase
- Explicit `sentry_sdk.capture_exception()` for critical handled failures:
  - Job failures (pipeline crashes before PR created)
  - Deploy failures (if applicable in this phase scope)
  - Verifier failures

### Claude's Discretion
- Exact systemd service name/path (`<service>` → e.g. `booty`)
- Breadcrumb instrumentation points (which requests/operations to breadcrumb)
- Integration test approach for "trigger error, event appears in Sentry"

</decisions>

<specifics>
## Specific Ideas

- Release and secrets must be physically separate: release.env (metadata, deploy-written) vs secrets.env (credentials, separate management)
- "Production without telemetry is a misconfigured system — better to refuse traffic than operate blind"
- Deploy failures in context: Phase 12 may only touch app-side Sentry; deploy.sh runs remotely. Verifier and job failures are in-app and should use capture_exception.

</specifics>

<deferred>
## Deferred Ideas

- Performance tracing (traces_sample_rate > 0) — future phase if desired

</deferred>

---

*Phase: 12-sentry-apm*
*Context gathered: 2026-02-15*
