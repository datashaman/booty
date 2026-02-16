# Booty

## What This Is

Booty is a self-managing software builder powered by AI. It receives GitHub issues via webhook, analyzes them with an LLM, generates code changes, runs tests with iterative refinement, and opens pull requests — including against its own repository with additional safety gates.

## Core Value

A Builder agent that can take a GitHub issue and produce a working PR with tested code — the foundation everything else builds on.

## Requirements

### Validated

- ✓ Builder agent picks up labeled GitHub issues via webhook — v1.0
- ✓ Builder clones target repo fresh for each task — v1.0
- ✓ Builder uses LLM (via magentic) to understand issue and produce code — v1.0
- ✓ Builder runs tests against the generated code — v1.0
- ✓ Builder opens a PR with the changes — v1.0
- ✓ Target repo is configurable (not hardcoded) — v1.0
- ✓ Builder can work on its own repo (self-management) — v1.0
- ✓ Issue filtering via specific GitHub label (e.g. `agent:builder`) — v1.0
- ✓ Webhook listener receives GitHub issue events — v1.0

### Validated (v1.1)

- ✓ Builder generates unit tests for changed files in every PR — v1.1
- ✓ Builder promotes PR from draft to ready-for-review when all tests pass — v1.1

### Validated (v1.2)

- ✓ Verifier agent runs on every PR, enforces gates only for agent PRs — v1.2
- ✓ Verifier runs tests in clean env, blocks PR if red (promotion + Checks API) — v1.2
- ✓ Verifier enforces diff limits (max_files_changed, max_diff_loc, max_loc_per_file) — v1.2
- ✓ Verifier validates .booty.yml schema — v1.2
- ✓ Verifier detects hallucinated imports / compile failures — v1.2

### Validated (v1.3)

- ✓ Automated deployment via GitHub Actions (SSH to DO, deploy.sh, health check) — v1.3
- ✓ Sentry APM integration for error tracking and release correlation — v1.3
- ✓ Observability agent ingests Sentry alerts via webhook — v1.3
- ✓ Alert-to-issue correlation (SHA, release, environment) — v1.3
- ✓ Filtering: severity threshold, error fingerprint dedup, cooldown per fingerprint — v1.3
- ✓ Auto-created GitHub issues with agent:builder label, severity, repro breadcrumbs — v1.3

### Validated (v1.6)

- ✓ Memory persists to append-only memory.jsonl with atomic writes — v1.6
- ✓ MemoryConfig (.booty.yml memory block) with env overrides — v1.6
- ✓ add_record API with 24h dedup by (type, repo, sha, fingerprint, pr_number) — v1.6
- ✓ Ingestion from Observability, Governor, Security, Verifier, Revert — v1.6
- ✓ Deterministic lookup (path/fingerprint, <1s for 10k records) — v1.6
- ✓ PR comment "Memory: related history" on Verifier check completion — v1.6
- ✓ Governor HOLD surfaces 1–2 memory links in PR comment — v1.6
- ✓ Observability incident "Related history" section — v1.6
- ✓ booty memory status | query --pr/--sha --json — v1.6
- ✓ Memory informational only; no outcomes blocked — v1.6

### Validated (v1.5)

- ✓ Security agent runs on pull_request opened/synchronize — v1.5
- ✓ Security publishes required GitHub check `booty/security` — v1.5
- ✓ Secret detection on changed files (gitleaks/trufflehog), FAIL + annotations — v1.5
- ✓ Dependency vulnerability gate (pip/npm/composer/cargo audit), FAIL on HIGH+ — v1.5
- ✓ Permission drift: sensitive paths → ESCALATE, override to Governor — v1.5
- ✓ Governor consumes Security risk override before deploy decisions — v1.5
- ✓ Security config block (.booty.yml): enabled, fail_severity, sensitive_paths — v1.5
- ✓ Security check completes in &lt; 60 seconds — v1.5

### Validated (v1.4)

- ✓ Governor gates production deployment (allow/hold) — v1.4
- ✓ Governor triggers deploy workflow via workflow_dispatch with exact SHA — v1.4
- ✓ Governor records release state (production_sha, deploy outcome) — v1.4
- ✓ Risk-based gating (LOW/MEDIUM/HIGH) from paths touched — v1.4
- ✓ Operator approval for HIGH risk (env/label/comment; env implemented, label/comment stubbed) — v1.4
- ✓ Cooldown and rate limits on deploy attempts — v1.4
- ✓ HOLD/ALLOW UX (status or issue with reason + unblock instructions) — v1.4
- ✓ Deploy failure → operator-visible GitHub issue — v1.4

### Deferred (v1.x+)

- [ ] Persistent cooldown store (OBSV-10) — deferred from v1.3
- [ ] Staging vs production deploy targets (DEPLOY-04)
- [ ] Rollback workflow (DEPLOY-05)

### Out of Scope

- Multi-agent coordination protocols — pain will reveal what's needed
- Builder generates integration tests — deferred; Verifier first
- Web UI or dashboard — CLI and GitHub are the interfaces
- Custom LLM fine-tuning — use off-the-shelf models via magentic
- Production deployment infrastructure — ✓ addressed in v1.3 (GitHub Actions deploy automation)

## Context

Shipped v1.0 with 3,012 LOC Python across 77 files.
Shipped v1.1 with test generation (convention detection, AST import validation) and PR promotion (draft → ready when tests+lint pass).
Shipped v1.2 with Verifier agent (GitHub Checks API, pull_request webhook, diff limits, .booty.yml schema v1, import/compile detection).
Shipped v1.3 with deploy automation (GitHub Actions → SSH → deploy.sh), Sentry APM (release/env correlation), and Observability agent (Sentry webhook → GitHub issues with agent:builder).
Shipped v1.4 with Release Governor — workflow_run trigger, risk scoring, approval policy, workflow_dispatch deploy, HOLD/ALLOW UX, release state store, booty governor CLI.
Shipped v1.5 with Security Agent — pull_request check booty/security, secret scanning (gitleaks/trufflehog), dependency audit (pip/npm/composer/cargo), permission drift → ESCALATE to Governor.
Shipped v1.6 with Memory Agent — append-only memory.jsonl, ingestion from Observability/Governor/Security/Verifier/Revert, deterministic lookup, PR/Governor/incident surfacing, booty memory status|query.
Tech stack: FastAPI, magentic, PyGithub, structlog, Pydantic Settings, sentry-sdk.
All v1.0 through v1.5 requirements satisfied.
Self-modification capability active with Verifier gates and protected paths.
Deployed on DigitalOcean via GitHub Actions workflow; Sentry error tracking with release correlation.

## Constraints

- **LLM Abstraction**: Magentic — keeps agent code readable, supports multiple backends
- **Language**: Python — scripts + API calls, no heavy framework
- **Trigger**: GitHub webhooks — event-driven, not polling
- **Workspace**: Fresh clone per task — clean isolation, no stale state
- **Interface**: GitHub issues in, PRs out — no custom UI

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Start with Builder only | Avoid protocol/abstraction quicksand; let pain reveal what's needed | ✓ Good — shipped complete pipeline |
| Magentic for LLM abstraction | Decorator-based, type-safe, multi-backend; keeps agent code clean | ✓ Good — clean prompt functions |
| GitHub webhooks for triggering | Event-driven is cleaner than polling; integrates with existing workflow | ✓ Good — FastAPI + HMAC working |
| Fresh clone per task | Isolation prevents stale state leaking between tasks; simplicity over speed | ✓ Good — clean workspace per job |
| Label-based issue filtering | Not every issue should trigger a build; explicit opt-in via label | ✓ Good — configurable trigger label |
| Pydantic Settings for config | Type-safe environment variable validation | ✓ Good — all config centralized |
| Full file generation (not diffs) | LLMs struggle with diffs; full file content is more reliable | ✓ Good — clean file writes |
| pathspec for path restrictions | Gitignore-style patterns with ** support | ✓ Good — reused for self-mod safety |
| Anthropic token counting API | Accurate budget management for context windows | ✓ Good — prevents overflow |
| giturlparse for self-detection | Handles HTTPS/SSH/.git/case variants for repo URL matching | ✓ Good — reliable self-target detection |
| Single LLM call for code + tests | Shared context, simpler architecture | ✓ Good — v1.1 |
| One-shot test generation, refine only code | Preserves refinement loop stability | ✓ Good — v1.1 |
| Multi-criteria PR promotion | Tests + linting + not self-modification | ✓ Good — v1.1 |
| AST parsing for import extraction | Handles edge cases vs regex | ✓ Good — v1.1 |
| File extension counting for language detection | 99%+ accuracy, zero dependencies | ✓ Good — v1.1 |
| GitHub App auth for Checks API | Verifier needs App token for check runs | ✓ Good — v1.2 |
| Builder never promotes; Verifier owns agent PR promotion | Clear ownership; single promotion path | ✓ Good — v1.2 |
| Early validation (schema + limits) before clone for agent PRs | Fail fast, no wasted clone | ✓ Good — v1.2 |
| install_command required for agent PRs with BootyConfigV1 | Import validation needs deps installed | ✓ Good — v1.2 |
| Push-to-main deploy trigger | Simplicity; staging/rollback deferred | ✓ Good — v1.3 |
| Release omitted when SENTRY_RELEASE empty | Never placeholder; deploy writes release.env | ✓ Good — v1.3 |
| In-memory cooldown for Sentry webhook | OBSV-10 persistent store deferred | ✓ Good — v1.3 |
| Retry only on 5xx for issue creation | 4xx (auth, not found) not retried | ✓ Good — v1.3 |
| workflow_dispatch-only deploy trigger | Governor owns deploy; verify-main runs on push | ✓ Good — v1.4 |
| Config from repo .booty.yml via GitHub API | Governor is multi-tenant; no local file | ✓ Good — v1.4 |
| gitleaks for secret scanning | Lightweight, diff-based; trufflehog acceptable | ✓ Good — v1.5 |
| Security runs on every PR | No is_agent_pr filter; consistent coverage | ✓ Good — v1.5 |
| ESCALATE does not block merge | Governor handles deploy gating; PR proceeds | ✓ Good — v1.5 |
| Override poll for race handling | Governor may run before Security; poll up to 120s | ✓ Good — v1.5 |
| Environment approval only for Phase 15 | Label/comment require PR lookup; deferred | ✓ Good — v1.4 |
| Memory block as raw dict; MemoryConfig validates on use | Unknown keys fail Memory only (MEM-25) | ✓ Good — v1.6 |
| Trigger Memory surfacing on check_run completed | Memory surfaces only after Verifier runs | ✓ Good — v1.6 |
| Governor section merges into existing Memory comment | Append or replace; single updatable comment | ✓ Good — v1.6 |
| Stdlib-only lookup; derive paths_hash from candidate paths | No new deps; verifier_cluster matches when caller has paths | ✓ Good — v1.6 |

## Current Milestone: v1.7 Planner Agent

**Goal:** Planner Agent turns input requests (issue, incident, operator prompt) into structured execution plans that Builder can consume without interpretation.

**Target features:**
- Accept inputs: GitHub issue (label `agent:plan`), Observability incident, operator CLI (`booty plan`)
- Produce Plan JSON (max 12 steps, schema with goal, risk_level, touch_paths, handoff_to_builder)
- Risk classification (LOW/MEDIUM/HIGH from touch_paths)
- Output: issue comment + stored artifact `$HOME/.booty/state/plans/<issue_id>.json`
- Idempotency: same plan for unchanged inputs within 24h (plan_hash for dedup)
- Builder contract: executable without interpretation

## Current State

**Shipped:** v1.6 (2026-02-16)

**What shipped in v1.6:**
- Memory Agent: append-only memory.jsonl, MemoryConfig, add_record API with dedup
- Ingestion from Observability, Governor, Security, Verifier, Revert (webhooks + runners + CLI)
- Deterministic lookup (path/fingerprint match, severity/recency sort)
- Surfacing: PR comment on Verifier check, Governor HOLD links, Observability incident "Related history"
- booty memory status | query CLI
- 28/28 v1.6 requirements; milestone audit passed

**What shipped in v1.5:**
- Security Agent: pull_request webhook, booty/security check (queued → in_progress → completed)
- Secret leakage detection (gitleaks/trufflehog on changed files, FAIL + annotations)
- Dependency vulnerability gate (pip/npm/composer/cargo audit, FAIL on severity >= HIGH)
- Permission drift: sensitive paths → ESCALATE, override persisted, Governor consumes
- 17/17 v1.5 requirements

<details>
<summary>v1.4 Release Governor (shipped 2026-02-16)</summary>

- Release Governor: workflow_run trigger, risk scoring (LOW/MEDIUM/HIGH), decision engine, cooldown/rate limit
- workflow_dispatch deploy with sha input; HOLD/ALLOW commit status (booty/release-governor)
- Release state store (.booty/state/release.json); deploy failure → GitHub issue
- booty governor status | simulate | trigger CLI; docs/release-governor.md
- 32/32 v1.4 requirements; milestone audit passed (tech_debt: label/comment approval stubbed)

</details>

---
*Last updated: 2026-02-16 — Milestone v1.7 Planner Agent started*
