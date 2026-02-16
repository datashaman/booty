# Milestone v1.4: Release Governor

**Status:** Planning
**Phases:** 14-17
**Requirements:** 32

## Overview

Release Governor gates production deployment. It runs when a verification workflow completes on main, computes risk from paths touched, enforces holds (deploy config missing, first-deploy approval, degraded+high-risk), triggers deploy via workflow_dispatch for allowed SHAs, records release state, and surfaces HOLD/ALLOW with clear operator UX.

## Phases

### Phase 14: Governor Foundation & Persistence ✓

**Goal:** Config schema, release state store, agent skeleton, deploy workflow sha input.

**Requirements:** GOV-04, GOV-19, GOV-20, GOV-21, GOV-22, GOV-26, GOV-27, GOV-28, GOV-29, GOV-30

**Success criteria:**
1. ReleaseGovernorConfig schema in .booty.yml (strict) with env overrides
2. File-based release.json at .booty/state/release.json; atomic write; single-writer safe
3. Delivery ID cache for idempotency; (repo, head_sha) dedup
4. New module `src/booty/release_governor/` with config + store
5. Deploy workflow accepts optional `sha` input for workflow_dispatch; checkout uses it
6. Verify-main workflow (runs on push to main, runs tests); deploy trigger changes to workflow_dispatch-only (Governor triggers)

**Depends on:** Nothing

**Plans:** 5 plans in 2 waves

Plans:
- [x] 14-01-PLAN.md — Config schema (ReleaseGovernorConfig, env overrides)
- [x] 14-02-PLAN.md — State store + delivery ID cache
- [x] 14-03-PLAN.md — Governor module skeleton + booty governor status
- [x] 14-04-PLAN.md — Deploy workflow sha input + deploy.sh DEPLOY_SHA
- [x] 14-05-PLAN.md — Verify-main workflow

---

### Phase 15: Trigger, Risk & Decision Logic

**Goal:** workflow_run handler, risk scoring from paths, decision rules, cooldown/rate limit.

**Requirements:** GOV-01, GOV-02, GOV-03, GOV-05, GOV-06, GOV-07, GOV-08, GOV-09, GOV-10, GOV-11, GOV-12, GOV-13

**Success criteria:**
1. Governor receives workflow_run (verification workflow on main, conclusion=success)
2. Uses head_sha from payload; fetches diff vs production_sha for risk
3. Risk scoring: HIGH (workflows, infra, lockfiles, migrations), MEDIUM (manifests), LOW (rest)
4. Hard holds: deploy not configured; first deploy without approval; degraded + high-risk
5. Approval policy: LOW auto-ALLOW; MEDIUM hold if incident; HIGH hold unless approval (env/label/comment)
6. Cooldown and max_deploys_per_hour enforced

**Depends on:** Phase 14

---

### Phase 16: Deploy Integration & Operator UX

**Goal:** workflow_dispatch deploy, HOLD/ALLOW UX, post-deploy observation, failure issues.

**Requirements:** GOV-14, GOV-15, GOV-16, GOV-17, GOV-18, GOV-23, GOV-24, GOV-25

**Success criteria:**
1. On ALLOW: POST workflow_dispatch with sha; update release state
2. On HOLD: commit status or issue with Decision, SHA, Risk, Reason, "How to unblock"
3. On ALLOW: status or comment with "Triggered: deploy workflow run <link>"
4. Governor observes deploy workflow_run completion; updates release state
5. Deploy failure → create/append GitHub issue with deploy-failure, severity:high, Actions link
6. Never deploys non-head_sha

**Depends on:** Phase 15

---

### Phase 17: CLI & Documentation

**Goal:** booty governor CLI and docs/release-governor.md.

**Requirements:** GOV-31, GOV-32

**Success criteria:**
1. `booty governor status` — show release state
2. `booty governor simulate --sha <sha>` — dry-run decision (no deploy)
3. `booty governor trigger --sha <sha>` — manual trigger (respects approval if HIGH risk)
4. docs/release-governor.md: configuration, approval mechanism, troubleshooting, manual test steps

**Depends on:** Phase 16

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GOV-01 | 15 | Pending |
| GOV-02 | 15 | Pending |
| GOV-03 | 15 | Pending |
| GOV-04 | 14 | Pending |
| GOV-05 | 15 | Pending |
| GOV-06 | 15 | Pending |
| GOV-07 | 15 | Pending |
| GOV-08 | 15 | Pending |
| GOV-09 | 15 | Pending |
| GOV-10 | 15 | Pending |
| GOV-11 | 15 | Pending |
| GOV-12 | 15 | Pending |
| GOV-13 | 15 | Pending |
| GOV-14 | 16 | Pending |
| GOV-15 | 16 | Pending |
| GOV-16 | 16 | Pending |
| GOV-17 | 16 | Pending |
| GOV-18 | 16 | Pending |
| GOV-19 | 14 | Pending |
| GOV-20 | 14 | Pending |
| GOV-21 | 14 | Pending |
| GOV-22 | 14 | Pending |
| GOV-23 | 16 | Pending |
| GOV-24 | 16 | Pending |
| GOV-25 | 16 | Pending |
| GOV-26 | 14 | Pending |
| GOV-27 | 14 | Pending |
| GOV-28 | 14 | Pending |
| GOV-29 | 14 | Pending |
| GOV-30 | 14 | Pending |
| GOV-31 | 17 | Pending |
| GOV-32 | 17 | Pending |

**Coverage:** 32/32 requirements mapped ✓

---
*Roadmap created: 2026-02-16*
