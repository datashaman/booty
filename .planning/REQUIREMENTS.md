# Requirements: Booty v1.4 Release Governor

**Defined:** 2026-02-16
**Core Value:** A Builder agent that can take a GitHub issue and produce a working PR with tested code — the foundation everything else builds on.

## v1.4 Requirements (This Milestone)

Requirements for Release Governor agent. Each maps to roadmap phases.

### Trigger & Inputs

- [x] **GOV-01**: Governor runs when a verification workflow completes successfully on main (workflow_run event, conclusion=success, head_sha)
- [x] **GOV-02**: Governor uses head_sha from event payload (never "latest main")
- [x] **GOV-03**: Governor receives optional Observability signal "is production degraded" (in-process state or Sentry; default unknown)
- [x] **GOV-04**: Governor loads config from env + optional .booty.yml; env overrides .booty.yml; strict schema (unknown keys fail)

### Decision & Risk

- [x] **GOV-05**: Governor computes risk_class (LOW | MEDIUM | HIGH) from paths touched vs production_sha
- [x] **GOV-06**: HIGH risk: workflow dirs, infra, auth-sensitive, lockfiles, migrations (configurable pathspecs)
- [x] **GOV-07**: MEDIUM risk: dependency manifests without lockfiles
- [x] **GOV-08**: Hard holds: deploy not configured; first deploy without approval (when required); degraded + high-risk
- [x] **GOV-09**: LOW risk: auto-ALLOW if Verifier passed and no active incident
- [x] **GOV-10**: MEDIUM risk: ALLOW if no incident; else HOLD
- [x] **GOV-11**: HIGH risk: HOLD unless operator approval exists (environment | label | comment)
- [x] **GOV-12**: Cooldown: no re-deploy of same SHA within N minutes after failure (default 30)
- [x] **GOV-13**: Rate limit: max M deploys per hour (default 6)

### Deploy Trigger & Post-Deploy

- [x] **GOV-14**: On ALLOW: dispatch deploy workflow via workflow_dispatch with sha=input
- [x] **GOV-15**: On HOLD: emit explanation (status or issue) with reason code and unblock instructions
- [x] **GOV-16**: Governor observes deploy outcome (workflow_run or deployment_status)
- [x] **GOV-17**: On deploy failure: create/append GitHub issue with deploy-failure, severity:high, link to Actions run
- [x] **GOV-18**: Governor never deploys a SHA that wasn't the verifier head_sha

### Persistence & Idempotency

- [x] **GOV-19**: Release state store: production_sha_current, production_sha_previous, last_deploy_attempt_sha, last_deploy_time, last_deploy_result, last_health_check
- [x] **GOV-20**: Store in file (.booty/state/release.json or similar); atomic writes; survives restarts
- [x] **GOV-21**: Dedup at (repo, head_sha); delivery ID caching for idempotency
- [x] **GOV-22**: Never trigger deploy twice for same SHA

### Operator UX

- [x] **GOV-23**: HOLD message: Decision, SHA, Risk, Reason code, "How to unblock"
- [x] **GOV-24**: ALLOW message: Decision, SHA, "Triggered: deploy workflow run &lt;link&gt;"
- [x] **GOV-25**: Single consistent UX pattern (commit status `booty/release-governor` OR issue comment — pick one)

### Config Schema

- [x] **GOV-26**: release_governor.enabled, production_environment_name, require_approval_for_first_deploy
- [x] **GOV-27**: release_governor.high_risk_paths, migration_paths (pathspecs)
- [x] **GOV-28**: release_governor.deploy_workflow_name, deploy_workflow_ref, cooldown_minutes, max_deploys_per_hour
- [x] **GOV-29**: release_governor.approval_mode (environment | label | comment); approval_label / approval_command when applicable

### Deliverables

- [x] **GOV-30**: New agent module `release_governor`
- [ ] **GOV-31**: docs/release-governor.md (config, approval, troubleshooting, manual test steps)
- [ ] **GOV-32**: CLI: `booty governor status`, `booty governor simulate --sha <sha>`, `booty governor trigger --sha <sha>`

## Future Requirements

Deferred to later milestones.

| ID | Requirement |
|----|-------------|
| OBSV-10 | Persistent cooldown store |
| DEPLOY-04 | Staging vs production deploy targets |
| DEPLOY-05 | Rollback workflow |
| GOV-ROLLBACK | Rollback automation (explicitly out of scope for v1.4) |

## Out of Scope (v1.4)

| Feature | Reason |
|---------|--------|
| Rollback automation | Spec: no auto-remediation |
| PR creation by Governor | Spec: no PR creation |
| Code edits by Governor | Spec: no code edits |
| Canary/gradual rollout | Spec: gate/hold/allow only |
| Complex RBAC | Spec: pick simplest approval mechanism |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GOV-01 | 15 | Complete |
| GOV-02 | 15 | Complete |
| GOV-03 | 15 | Complete |
| GOV-04 | 14 | Complete |
| GOV-05 | 15 | Complete |
| GOV-06 | 15 | Complete |
| GOV-07 | 15 | Complete |
| GOV-08 | 15 | Complete |
| GOV-09 | 15 | Complete |
| GOV-10 | 15 | Complete |
| GOV-11 | 15 | Complete |
| GOV-12 | 15 | Complete |
| GOV-13 | 15 | Complete |
| GOV-14 | 16 | Complete |
| GOV-15 | 16 | Complete |
| GOV-16 | 16 | Complete |
| GOV-17 | 16 | Complete |
| GOV-18 | 16 | Complete |
| GOV-19 | 14 | Complete |
| GOV-20 | 14 | Complete |
| GOV-21 | 14 | Complete |
| GOV-22 | 14 | Complete |
| GOV-23 | 16 | Complete |
| GOV-24 | 16 | Complete |
| GOV-25 | 16 | Complete |
| GOV-26 | 14 | Complete |
| GOV-27 | 14 | Complete |
| GOV-28 | 14 | Complete |
| GOV-29 | 14 | Complete |
| GOV-30 | 14 | Complete |
| GOV-31 | 17 | Pending |
| GOV-32 | 17 | Pending |

**Coverage:**
- v1.4 requirements: 32 total
- Mapped to phases: 32
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-16*
*Last updated: 2026-02-16 after initial definition*
