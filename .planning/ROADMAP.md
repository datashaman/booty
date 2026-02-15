# Roadmap: Booty

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-02-14)
- ✅ **v1.1 Test Generation & PR Promotion** — Phases 5-6 (shipped 2026-02-15)
- ✅ **v1.2 Verifier Agent** — Phases 7-10 (shipped 2026-02-15)
- ◇ **v1.3 Observability** — Phases 11-13 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-02-14</summary>

Delivered a Builder agent that picks up GitHub issues, writes code via LLM, runs tests with iterative refinement, and opens PRs — including against its own repository.

**Stats:** 77 files, 3,012 LOC Python, 4 phases, 13 plans, 1 day execution

See [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) and [MILESTONES.md](MILESTONES.md) for details.

</details>

<details>
<summary>✅ v1.1 Test Generation & PR Promotion (Phases 5-6) — SHIPPED 2026-02-15</summary>

Builder generates unit tests for all changed files and promotes draft PRs to ready-for-review when tests and linting pass.

**Stats:** 4 plans, 2 phases, 41 files modified (v1.0..v1.1)

See [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md) and [MILESTONES.md](MILESTONES.md) for details.

</details>

<details>
<summary>✅ v1.2 Verifier Agent (Phases 7-10) — SHIPPED 2026-02-15</summary>

Verifier agent runs on every PR, runs tests in clean env, enforces diff limits, validates .booty.yml, detects import/compile failures, posts check run `booty/verifier`.

**Stats:** 68 files modified (v1.1..v1.2), 4 phases, 12 plans

See [milestones/v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md) and [MILESTONES.md](MILESTONES.md) for details.

</details>

---

## Progress

| Phase | Milestone | Goal | Status |
|-------|-----------|------|--------|
| 1. Foundation | v1.0 | Webhook, clone, job queue | Complete |
| 2. GitHub Integration | v1.0 | LLM, PR creation | Complete |
| 3. Test-Driven Refinement | v1.0 | Tests, refinement loop | Complete |
| 4. Self-Modification Safety | v1.0 | Protected paths, draft PR | Complete |
| 5. Test Generation | v1.1 | Unit tests for changed files | Complete |
| 6. PR Promotion | v1.1 | Draft → ready when green | Complete |
| 7. GitHub App + Checks | v1.2 | Checks API integration | Complete |
| 8. Verifier Runner | v1.2 | PR webhook, clone, test, check | Complete |
| 9. Diff Limits + Schema | v1.2 | Limits, .booty.yml v1 | Complete |
| 10. Import/Compile Detection | v1.2 | Hallucination detection | Complete |
| 11. Deploy Automation | v1.3 | GitHub Actions → SSH → DO, deploy.sh | Complete |
| 12. Sentry APM | v1.3 | Error tracking, release/SHA correlation | Complete |
| 13. Observability Agent | v1.3 | Sentry webhook → filter → GitHub issues | Pending |

---

## Phase Details (v1.3)

### Phase 11: Deploy Automation

**Goal:** Automated deployment via GitHub Actions — push to main triggers SSH to DigitalOcean, runs deploy.sh, restarts Booty.

**Requirements:** DEPLOY-01, DEPLOY-02, DEPLOY-03

**Plans:** 1 plan

Plans:
- [x] 11-01-PLAN.md — Deploy workflow (trigger, preflight, paths-filter, ssh-agent, deploy.sh, health check)

**Success criteria:**
1. Workflow file exists at `.github/workflows/deploy.yml`
2. Workflow triggers on `push` to `main` branch
3. Workflow SSHs to deploy host and executes deploy steps (or invokes deploy.sh)
4. Booty service restarts after deploy
5. SSH key stored as GitHub secret; not in workflow file

### Phase 12: Sentry APM

**Goal:** Sentry SDK integrated for error tracking; release and environment set for deploy correlation.

**Requirements:** APM-01, APM-02, APM-03

**Plans:** 2 plans

Plans:
- [x] 12-01-PLAN.md — SDK integration (dependency, config, init, deploy release.env, systemd)
- [x] 12-02-PLAN.md — capture_exception (job + verifier), verification test, manual route

**Success criteria:**
1. `sentry-sdk` added to dependencies
2. `sentry_sdk.init()` called at app startup with DSN from env
3. `release` set to git SHA (from env or deploy)
4. `environment` set (e.g., "production")
5. FastAPI integration enabled; unhandled exceptions captured
6. Test: Trigger error in app; event appears in Sentry with correct release

### Phase 13: Observability Agent

**Goal:** Sentry webhook → verify → filter (severity, dedup, cooldown) → create GitHub issue with agent:builder label.

**Requirements:** OBSV-01 through OBSV-08

**Plans:** 2 plans

Plans:
- [ ] 13-01-PLAN.md — Webhook route, HMAC verify, severity/dedup/cooldown filters
- [ ] 13-02-PLAN.md — Issue body builder, create_issue, retry, spool, wire to route

**Success criteria:**
1. POST route for Sentry webhook (e.g., `/webhooks/sentry`)
2. HMAC-SHA256 verification of `Sentry-Hook-Signature` before processing
3. Configurable severity threshold filters low-severity alerts
4. Dedup by fingerprint; cooldown per fingerprint prevents duplicate issues
5. Creates GitHub issue with `agent:builder` label when alert passes filters
6. Issue body includes severity, release/SHA, environment, breadcrumbs
7. Issue links to Sentry event/issue URL for traceability
8. Builder can pick up created issues (existing flow)

---
*Last updated: 2026-02-15 — v1.3 roadmap created*
