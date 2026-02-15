# Requirements: Booty

**Defined:** 2026-02-15
**Core Value:** A Builder agent that can take a GitHub issue and produce a working PR with tested code — the foundation everything else builds on.

## v1.3 Requirements (Observability)

Requirements for milestone v1.3. Each maps to roadmap phases.

### Deploy Automation

- [x] **DEPLOY-01**: GitHub Actions workflow triggers on push to main branch
- [x] **DEPLOY-02**: Workflow SSHs to DigitalOcean server and runs deploy.sh (or equivalent)
- [x] **DEPLOY-03**: Deployment restarts Booty service (systemctl) after pulling and installing

### Sentry APM

- [x] **APM-01**: Sentry SDK integrated with FastAPI app; errors and exceptions captured
- [x] **APM-02**: Release set to git SHA (or equivalent) for deploy correlation
- [x] **APM-03**: Environment tag set (e.g., production) for filtering in Sentry UI

### Observability Agent

- [ ] **OBSV-01**: Observability agent exposes POST webhook route for Sentry alerts
- [ ] **OBSV-02**: Webhook verifies Sentry-Hook-Signature via HMAC-SHA256 before processing
- [ ] **OBSV-03**: Filter by configurable severity threshold (e.g., error and above)
- [ ] **OBSV-04**: Deduplicate by error fingerprint (one issue per unique error pattern)
- [ ] **OBSV-05**: Cooldown per fingerprint prevents duplicate issues within configurable window
- [ ] **OBSV-06**: Creates GitHub issue with agent:builder label when alert passes filters
- [ ] **OBSV-07**: Issue body includes severity, release/SHA, environment, repro breadcrumbs (from Sentry event)
- [ ] **OBSV-08**: Alert-to-issue correlation: issue links to Sentry event/issue for traceability

## Future Requirements (v1.x+)

Deferred to future releases.

### Observability

- **OBSV-09**: Multiple Sentry projects or environments with routing rules
- **OBSV-10**: Persistent cooldown store (e.g., Redis) survives restarts
- **OBSV-11**: Observability agent metrics (e.g., webhooks received, issues created)

### Deploy

- **DEPLOY-04**: Staging vs production deploy targets
- **DEPLOY-05**: Rollback workflow

## Out of Scope

| Feature | Reason |
|---------|--------|
| Custom APM from scratch | Sentry is mature; reinventing is high cost |
| Observability dashboard | CLI and GitHub are interfaces; use Sentry UI |
| Polling Sentry API | Webhook (push) is lower latency, no rate limits |
| Slack/Discord for alerts | GitHub-centric model; issues are the interface |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEPLOY-01 | Phase 11 | Complete |
| DEPLOY-02 | Phase 11 | Complete |
| DEPLOY-03 | Phase 11 | Complete |
| APM-01 | Phase 12 | Complete |
| APM-02 | Phase 12 | Complete |
| APM-03 | Phase 12 | Complete |
| OBSV-01 | Phase 13 | Pending |
| OBSV-02 | Phase 13 | Pending |
| OBSV-03 | Phase 13 | Pending |
| OBSV-04 | Phase 13 | Pending |
| OBSV-05 | Phase 13 | Pending |
| OBSV-06 | Phase 13 | Pending |
| OBSV-07 | Phase 13 | Pending |
| OBSV-08 | Phase 13 | Pending |

**Coverage:**
- v1.3 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-15*
*Last updated: 2026-02-15 after initial definition*
