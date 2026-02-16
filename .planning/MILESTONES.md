# Project Milestones: Booty

## v1.5 Security Agent (Shipped: 2026-02-16)

**Delivered:** Security Agent as merge veto authority — pull_request check `booty/security`, secret scanning (gitleaks/trufflehog), dependency audit (pip/npm/composer/cargo), permission drift → ESCALATE to Governor.

**Phases completed:** 18-21 (10 plans total)

**Key accomplishments:**

- SecurityConfig schema, booty/security check, pull_request webhook, Security module skeleton (Phase 18)
- Secret leakage detection: gitleaks/trufflehog on changed files, FAIL + file/line annotations (Phase 19)
- Dependency vulnerability gate: lockfile auto-detect, per-ecosystem audit, FAIL on severity >= HIGH (Phase 20)
- Permission drift: sensitive paths → ESCALATE, override persisted to security_overrides.json (Phase 21)
- Governor override integration: get_security_override with poll, risk_class=HIGH when present (Phase 21)
- 17/17 v1.5 requirements

**Stats:**

- 70 files modified (v1.4..v1.5)
- 10,945 lines of Python (total)
- 4 phases, 10 plans
- 1 day from v1.4 to ship (2026-02-16)

**Git range:** `7f59bf0` (v1.4) → `666b7dd` (HEAD)

**What's next:** TBD — run `/gsd:new-milestone` to define

---

## v1.4 Release Governor (Shipped: 2026-02-16)

**Delivered:** Governor gates production deployment — workflow_run trigger, risk scoring from paths touched, approval policy (env/label/comment; env implemented), workflow_dispatch deploy for allowed SHAs, release state store, HOLD/ALLOW commit status, deploy failure issues.

**Phases completed:** 14-17 (13 plans total)

**Key accomplishments:**

- ReleaseGovernorConfig schema, env overrides, file-based release.json, delivery ID cache for idempotency
- risk.py compute_risk_class (LOW/MEDIUM/HIGH from pathspec); decision.py compute_decision; cooldown/rate limit
- workflow_run webhook handler; config from repo .booty.yml via GitHub API
- deploy.py dispatch_deploy; ux.py post_hold_status/post_allow_status; deploy outcome observation
- booty governor status | simulate | trigger CLI; docs/release-governor.md
- 32/32 v1.4 requirements; milestone audit passed (tech_debt: label/comment approval stubbed)

**Stats:**

- 74 files modified (v1.3..v1.4)
- 8,638 lines of Python (total)
- 4 phases, 13 plans
- 1 day from v1.3 to ship (2026-02-15 → 2026-02-16)

**Git range:** `7bbc939` (v1.3) → `7f59bf0` (Merge PR #22)

**What's next:** TBD — run `/gsd:new-milestone` to define

---

## v1.3 Observability (Shipped: 2026-02-15)

**Delivered:** Close the post-merge loop — automated deployment via GitHub Actions, Sentry APM for error tracking, and Observability agent that turns Sentry alerts into GitHub issues with agent:builder label.

**Phases completed:** 11-13 (5 plans total)

**Key accomplishments:**

- GitHub Actions deploy workflow (push to main, paths-filter, ssh-agent, deploy.sh, health check)
- Sentry SDK integrated with FastAPI; release/env from deploy for correlation
- capture_exception in job and verifier failure handlers; GET /internal/sentry-test for E2E
- POST /webhooks/sentry with HMAC verify, severity/dedup/cooldown filters
- create_issue_from_sentry_event with agent:builder label, retry, spool
- 15/15 v1.3 requirements; milestone audit passed

**Stats:**

- 58 files modified (v1.2..v1.3)
- 6,805 lines of Python (total)
- 3 phases, 5 plans
- 1 day from v1.2 to ship (2026-02-15)

**Git range:** `3afc78a` (docs: start milestone v1.3) → `ca1885d` (Merge PR #13)

**What's next:** TBD — run `/gsd:new-milestone` to define

---

## v1.2 Verifier Agent (Shipped: 2026-02-15)

**Delivered:** Verifier agent runs on every PR, runs tests in clean env, enforces diff limits, validates .booty.yml, detects import/compile failures, posts check run `booty/verifier`.

**Phases completed:** 7-10 (12 plans total)

**Key accomplishments:**

- GitHub App + Checks API integration (create_check_run, edit_check_run) with booty status and booty verifier check-test CLI
- Verifier runner with VerifierJob, prepare_verification_workspace, process_verifier_job — check lifecycle queued → in_progress → completed
- pull_request webhook, VerifierQueue with dedup, agent:builder label, Builder never promotes — Verifier owns promotion and failure comments
- BootyConfigV1 schema with load_booty_config_from_content; verifier/limits.py (max_files_changed, max_diff_loc, max_loc_per_file)
- verifier/imports.py: compile_sweep, validate_imports; full pipeline setup → install → import/compile → tests
- 12/12 v1.2 requirements satisfied; milestone audit passed

**Stats:**

- 68 files modified (v1.1..v1.2)
- 5,615 lines of Python (total)
- 4 phases, 12 plans
- 1 day from v1.1 to ship (2026-02-15)

**Git range:** `0238b69` (docs: start milestone v1.2) → `aaca2ee` (Merge PR #9)

**What's next:** TBD — run `/gsd:new-milestone` to define

---

## v1.1 Test Generation & PR Promotion (Shipped: 2026-02-15)

**Delivered:** Builder generates unit tests for all changed files and promotes draft PRs to ready-for-review when tests and linting pass.

**Phases completed:** 5-6 (4 plans total)

**Key accomplishments:**

- Convention detection module with language-agnostic test conventions and AST-based import validation
- LLM integration for single-call code+test generation using detected conventions
- Promotion module with GraphQL promote_to_ready_for_review and tenacity retry (5xx/network only)
- Pipeline wiring: quality checks for all jobs, draft PRs promoted when tests+lint pass (self-mod excluded)
- 8/8 v1.1 requirements satisfied

**Stats:**

- 41 files modified (v1.0..v1.1)
- ~5,000 net LOC added (4,052 total Python)
- 2 phases, 4 plans
- 1 day from v1.0 to ship (2026-02-14 → 2026-02-15)

**Git range:** `efac606` (docs: start milestone v1.1) → `3e2e17c` (docs(05): add Phase 5 verification)

**What's next:** TBD — run `/gsd:new-milestone` to define

---

## v1.0 MVP (Shipped: 2026-02-14)

**Delivered:** A Builder agent that picks up GitHub issues, writes code via LLM, runs tests with iterative refinement, and opens PRs — including against its own repository.

**Phases completed:** 1-4 (13 plans total)

**Key accomplishments:**

- FastAPI webhook receiver with HMAC-SHA256 verification and async job queue with worker pool
- End-to-end LLM code generation pipeline transforming GitHub issues into pull requests in 12 steps
- Iterative test-driven refinement with failure feedback loops and exponential backoff
- Self-modification capability with protected path enforcement, quality gates (ruff), and draft PR safety
- 17/17 v1 requirements satisfied with 100% milestone audit pass

**Stats:**

- 77 files created/modified
- 3,012 lines of Python
- 4 phases, 13 plans
- 1 day from init to ship (2026-02-14)

**Git range:** `6d6b356` (docs: initialize project) → `9a70cae` (docs(04): complete self-modification phase)

**What's next:** v1.1 — TBD (run `/gsd:new-milestone` to define)

---
