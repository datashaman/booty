# Project Research Summary

**Project:** Booty
**Domain:** Observability — deploy automation, Sentry APM, alert-to-issue pipeline
**Researched:** 2026-02-15
**Confidence:** HIGH

## Executive Summary

v1.3 adds three capabilities: (1) automated deploy via GitHub Actions and existing deploy.sh, (2) Sentry APM for error tracking and release correlation, and (3) an Observability agent that receives Sentry webhooks, filters by severity/dedup/cooldown, and creates GitHub issues with agent:builder for Builder intake. The recommended approach reuses Booty's FastAPI + webhook patterns. Key risks: alert storm without filtering, and skipping webhook signature verification. Both are addressed in the Observability agent design.

## Key Findings

### Recommended Stack

**Core:** sentry-sdk (Python) for APM; GitHub Actions for deploy; stdlib hmac for webhook verification.
**Integration:** sentry_sdk.init() at app startup with `release` = git SHA; deploy workflow triggers on push to main; Observability agent adds one POST route.
**Avoid:** Polling Sentry API; custom APM; storing secrets in code.

### Expected Features

**Must have (table stakes):** Deploy on merge; error tracking with release correlation; webhook verification; severity filter; fingerprint dedup; cooldown per fingerprint; auto-created GitHub issues with agent:builder.
**Should have:** Repro breadcrumbs in issue body; environment + release tags.
**Defer:** Multi-environment routing; persistent cooldown store; dashboard.

### Architecture Approach

New `observability/` subsystem with webhook handler, filters, and issue creator. Deploy workflow in .github/workflows/deploy.yml. Sentry SDK initialized in main.py before app creation.

**Major components:**
1. Deploy workflow — triggers on main, SSH to DO, runs deploy.sh, passes SHA if needed
2. Sentry SDK — init in main; FastAPI integration; release = SHA
3. Observability agent — webhook route, verify, filter, create issue

### Critical Pitfalls

1. **No webhook verify** — Always HMAC-verify Sentry-Hook-Signature
2. **Alert storm** — Dedup by fingerprint + cooldown; severity threshold
3. **Release not set** — Pass git SHA from deploy to sentry_sdk.init
4. **SSH key exposure** — Use GitHub secrets only; never log
5. **Secret mismatch** — Document env name; test webhook in dev

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 11: Deploy Automation
**Rationale:** Foundation; enables repeatable deploys and SHA for release tagging.
**Delivers:** .github/workflows/deploy.yml; trigger on main; SSH to DO; run deploy.sh.
**Addresses:** Automated deployment (PROJECT.md Active v1.3).
**Avoids:** Manual deploy drift; no SHA for Sentry.

### Phase 12: Sentry APM
**Rationale:** Error tracking before Observability agent; release correlation depends on this.
**Delivers:** sentry-sdk in app; release = git SHA; environment; FastAPI integration.
**Addresses:** Sentry APM integration (PROJECT.md Active v1.3).
**Uses:** sentry-sdk, FastAPI integration from STACK.md.

### Phase 13: Observability Agent
**Rationale:** Closes loop; Sentry alerts → GitHub issues → Builder.
**Delivers:** Webhook route; HMAC verify; filters (severity, dedup, cooldown); issue creation with agent:builder, severity, breadcrumbs, release.
**Addresses:** Observability agent, alert-to-issue correlation, filtering, auto-created issues (PROJECT.md Active v1.3).
**Avoids:** Alert storm, unverified webhooks from PITFALLS.md.

### Phase Ordering Rationale

- Deploy first: Enables SHA at deploy time; needed for Sentry release.
- Sentry APM second: App must send events before Observability agent can correlate.
- Observability agent third: Consumes Sentry webhooks; depends on Sentry project + DSN.

### Research Flags

- **Phase 11:** Straightforward; deploy.sh exists; workflow pattern well-known.
- **Phase 12:** Straightforward; Context7 verified FastAPI + release.
- **Phase 13:** Verify Sentry issue-alert payload structure (event_alert vs metric_alert) during planning.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Context7 + deploy.sh verified |
| Features | HIGH | PROJECT.md Active aligned with research |
| Architecture | HIGH | Mirrors builder/verifier patterns |
| Pitfalls | HIGH | Standard webhook/APM gotchas |

**Overall confidence:** HIGH

### Gaps to Address

- **Sentry payload variants:** Issue alerts vs metric alerts may differ; plan-phase should confirm payload shape for filtering (severity, fingerprint).
- **Cooldown persistence:** MVP uses in-memory; document upgrade path to Redis if needed.

## Sources

### Primary (HIGH confidence)
- /getsentry/sentry-python — FastAPI, release
- /getsentry/sentry-docs — Webhook signature, payload
- deploy.sh — Existing deploy flow

### Secondary (MEDIUM confidence)
- Web search — Sentry issue alert payload (action=triggered, event_alert)

---
*Research completed: 2026-02-15*
*Ready for roadmap: yes*
