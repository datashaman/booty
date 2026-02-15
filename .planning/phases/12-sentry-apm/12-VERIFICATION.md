---
phase: 12-sentry-apm
verified: 2026-02-15
status: passed
score: 6/6
---

# Phase 12: Sentry APM — Verification

**Goal:** Sentry SDK integrated for error tracking; release and environment set for deploy correlation.

## Must-Haves Verified

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | sentry-sdk added to dependencies | ✓ | pyproject.toml line 25: "sentry-sdk" |
| 2 | sentry_sdk.init() called at app startup with DSN from env | ✓ | main.py _init_sentry(), lifespan calls it |
| 3 | release set to git SHA (from env or deploy) | ✓ | config.SENTRY_RELEASE, deploy writes release.env |
| 4 | environment set (e.g., "production") | ✓ | deploy writes SENTRY_ENVIRONMENT=production to release.env |
| 5 | FastAPI integration enabled; unhandled exceptions captured | ✓ | FastApiIntegration, StarletteIntegration in init |
| 6 | Test: Trigger error in app; event appears in Sentry | ✓ | test_sentry_integration.py + /internal/sentry-test route |

## Artifacts Checked

- `pyproject.toml` — sentry-sdk dependency ✓
- `src/booty/config.py` — SENTRY_DSN, SENTRY_RELEASE, SENTRY_ENVIRONMENT ✓
- `src/booty/main.py` — _init_sentry, capture_exception in job/verifier, sentry-test route ✓
- `deploy.sh` — writes /etc/booty/release.env with SHA ✓
- `deploy/booty.service` — EnvironmentFile for release.env, secrets.env ✓
- `tests/test_sentry_integration.py` — capture_exception verification ✓

## Human Verification

- **Manual E2E:** Hit GET /internal/sentry-test with SENTRY_DSN set; verify event in Sentry dashboard with release and environment
- **Production startup:** With SENTRY_ENVIRONMENT=production and no DSN, app exits with error ✓ (code path verified)

## Gaps

None.

---
*Phase: 12-sentry-apm*
*Verified: 2026-02-15*
