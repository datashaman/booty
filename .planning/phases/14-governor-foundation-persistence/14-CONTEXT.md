# Phase 14: Governor Foundation & Persistence - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Config schema, release state store, agent skeleton, deploy workflow sha input, and verify-main workflow wiring. Governor decides allow/hold and triggers deploy in Phase 15; this phase delivers the foundation: config in .booty.yml, persistent state with idempotency, placeholder handlers, deploy workflow that accepts sha, and a new verify-main workflow that runs on push to main.

</domain>

<decisions>
## Implementation Decisions

### Config schema integration
- Top-level key `release_governor: {...}` in `.booty.yml`, alongside existing keys
- Extend BootyConfigV1 with optional `release_governor` block; absent/empty = Governor disabled
- Env override prefix: `RELEASE_GOVERNOR_*` (e.g. `RELEASE_GOVERNOR_ENABLED`, `RELEASE_GOVERNOR_COOLDOWN_MINUTES`)
- When disabled: Governor module loaded but no-op — config loads, handlers skip

### State store layout & durability
- Separate files: `release.json` for release state, `delivery_ids.json` (or similar) for delivery ID cache
- File locking (fcntl/flock) for safe reads/writes across processes
- `.booty/state/` created at startup when Governor module loads
- `release.json` exists with null/empty fields even before first deploy (e.g. `production_sha_current: null`)
- State directory: app/data directory (e.g. `$HOME/.booty/state/` or configurable path), not inside the repo

### Workflow transition
- New workflow: `verify-main.yml` runs on push to main; mirrors Verifier logic (tests, lint, schema validation) — reuse Verifier code (DRY)
- Deploy workflow: add optional `sha` input for workflow_dispatch; checkout uses it when provided
- Deploy fails immediately if `sha` omitted — even manual workflow_dispatch must pass sha explicitly
- Keep deploy push trigger in Phase 14; remove push trigger in Phase 15 when Governor can trigger
- Governor triggers deploy with `deploy_workflow_ref` from config (supports branch/tag)

### Agent skeleton scope
- Config + store + delivery cache + placeholder handler stubs; handlers no-op until Phase 15
- Handler stubs: same signature as Phase 15 — accept workflow_run payload, body is no-op
- No webhook route in Phase 14 — Phase 15 adds it when workflow_run handling ships
- Governor module internal only — consumed by router/webhook layer when added in Phase 15
- Minimal CLI: `booty governor status` — loads config to determine enabled/disabled; when enabled with no deploys yet, show full skeleton (`production_sha_current: null`, `last_deploy_time: null`, etc.)

### Claude's Discretion
- Exact state directory path and config key (if configurable)
- Structure of `delivery_ids.json` (e.g. list vs object keyed by "repo:sha")
- Exact env var names beyond `RELEASE_GOVERNOR_*` prefix mapping
- Lock scope (per-file vs per-operation) and lock acquisition details

</decisions>

<specifics>
## Specific Ideas

No specific references or "like X" moments — standard approaches acceptable.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-governor-foundation-persistence*
*Context gathered: 2026-02-16*
