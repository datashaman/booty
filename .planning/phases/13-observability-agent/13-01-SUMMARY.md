---
phase: 13-observability-agent
plan: 01
subsystem: observability
tags: [sentry, webhook, hmac, fastapi]

requires:
  - phase: 12-sentry-apm
    provides: Sentry SDK integration, release/environment
provides:
  - POST /webhooks/sentry with HMAC-SHA256 verification
  - event_alert filtering, severity threshold, in-memory cooldown by issue_id
affects: 13-02 (issue creation)

tech-stack:
  added: []
  patterns: [Sentry webhook ingestion, in-memory dedup/cooldown]

key-files:
  created: []
  modified: [src/booty/config.py, src/booty/webhooks.py, .env.example]

key-decisions:
  - "SENTRY_WEBHOOK_SECRET required at startup (no dev exception per CONTEXT)"
  - "In-memory cooldown store; OBSV-10 persistent store deferred"

patterns-established:
  - "Sentry webhook: raw body first, HMAC verify, then parse JSON"

duration: 15min
completed: 2026-02-15
---

# Phase 13 Plan 01: Sentry Webhook Route Summary

**POST /webhooks/sentry with HMAC verification, event_alert filtering, severity/dedup/cooldown**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-15
- **Completed:** 2026-02-15
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- SENTRY_WEBHOOK_SECRET, OBSV_MIN_SEVERITY, OBSV_COOLDOWN_HOURS in Settings
- verify_sentry_signature() for Sentry-Hook-Signature HMAC-SHA256
- _severity_rank() for configurable severity filtering
- POST /webhooks/sentry: event_alert only, 401/422/200 responses
- In-memory cooldown by issue_id per OBSV_COOLDOWN_HOURS

## Task Commits

1. **Task 1: Add observability config and verify HMAC** - `d129b9b` (feat)
2. **Task 2: Add POST /webhooks/sentry route with filters** - `2178a7a` (feat)

**Plan metadata:** pending

## Files Created/Modified
- `src/booty/config.py` - SENTRY_WEBHOOK_SECRET, OBSV_* settings
- `src/booty/webhooks.py` - verify_sentry_signature, _severity_rank, sentry_webhook route
- `.env.example` - SENTRY_WEBHOOK_SECRET, OBSV_* placeholders

## Decisions Made
- SENTRY_WEBHOOK_SECRET required (no default) per CONTEXT
- In-memory cooldown; persistent store (OBSV-10) deferred

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## Next Phase Readiness
- Webhook route accepts/validates Sentry alerts
- Plan 02 will add issue creation (create_issue_from_sentry_event) and wire to route

---
*Phase: 13-observability-agent*
*Completed: 2026-02-15*
