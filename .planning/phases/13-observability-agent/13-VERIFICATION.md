# Phase 13: Observability Agent — Verification

**Goal:** Sentry webhook → verify → filter (severity, dedup, cooldown) → create GitHub issue with agent:builder label.

**Verified:** 2026-02-15

## status: passed

## Must-Haves Checked Against Codebase

| # | Must-Have | Status | Evidence |
|---|-----------|--------|----------|
| 1 | POST route for Sentry webhook | ✓ | `webhooks.py` @router.post("/sentry"), prefix /webhooks → /webhooks/sentry |
| 2 | HMAC-SHA256 verification of Sentry-Hook-Signature | ✓ | `verify_sentry_signature()` uses hmac.new(sha256), compare_digest |
| 3 | Configurable severity threshold | ✓ | `OBSV_MIN_SEVERITY` in config, `_severity_rank()` filter |
| 4 | Dedup by fingerprint (issue_id) | ✓ | `_obsv_seen` dict, one issue per issue_id |
| 5 | Cooldown per fingerprint | ✓ | `OBSV_COOLDOWN_HOURS`, window_sec check before create |
| 6 | Creates GitHub issue with agent:builder label | ✓ | `create_issue_from_sentry_event` uses TRIGGER_LABEL |
| 7 | Issue body: severity, release, environment, Sentry link, breadcrumbs | ✓ | `build_sentry_issue_body` includes all |
| 8 | Builder picks up created issues | ✓ | agent:builder label matches existing webhook flow |

## Artifacts Verified

- `src/booty/webhooks.py` — Sentry route, verify, filter, wire to issue creator
- `src/booty/config.py` — SENTRY_WEBHOOK_SECRET, OBSV_MIN_SEVERITY, OBSV_COOLDOWN_HOURS
- `src/booty/github/issues.py` — create_issue_from_sentry_event, retry, spool
- `build_sentry_issue_body` — severity, env, release, Sentry link, top 7 frames, breadcrumbs

## Gaps

None.
