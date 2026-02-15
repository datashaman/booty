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

### Active (v1.3)

- [ ] Automated deployment via GitHub Actions (SSH to DO, pull, install, restart)
- [ ] Sentry APM integration for error tracking and release correlation
- [ ] Observability agent ingests Sentry alerts via webhook
- [ ] Alert-to-issue correlation (SHA, release, environment)
- [ ] Filtering: severity threshold, error fingerprint dedup, cooldown per fingerprint
- [ ] Auto-created GitHub issues with agent:builder label, severity, repro breadcrumbs

### Out of Scope

- Multi-agent coordination protocols — pain will reveal what's needed
- Planner/Architect agents — future agents added incrementally
- Builder generates integration tests — deferred; Verifier first
- Web UI or dashboard — CLI and GitHub are the interfaces
- Custom LLM fine-tuning — use off-the-shelf models via magentic
- Production deployment infrastructure — ~~runs locally first~~ addressed in v1.3 (deploy automation)

## Context

Shipped v1.0 with 3,012 LOC Python across 77 files.
Shipped v1.1 with test generation (convention detection, AST import validation) and PR promotion (draft → ready when tests+lint pass).
Shipped v1.2 with Verifier agent (GitHub Checks API, pull_request webhook, diff limits, .booty.yml schema v1, import/compile detection).
Tech stack: FastAPI, magentic, PyGithub, structlog, Pydantic Settings.
All v1.0, v1.1, v1.2 requirements satisfied.
Self-modification capability active with Verifier gates and protected paths.
Deployed on DigitalOcean (systemd + nginx + uvicorn unix socket). Manual deploy via deploy.sh (SSH + git pull).
No APM/monitoring in place yet — greenfield for observability.

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

## Current Milestone: v1.3 Observability

**Goal:** Close the post-merge loop — production errors automatically flow back as GitHub issues for Builder intake.

**Target features:**
- Automated deployment via GitHub Actions (deploy.sh → CI/CD)
- Sentry APM integration (error tracking, release/SHA correlation)
- Observability agent (Sentry webhook → filtered → GitHub issues with repro context)

## Current State

**Shipped:** v1.2 (2026-02-15)
**Current Milestone:** v1.3 Observability

**What shipped in v1.2:**
- Verifier runs on every PR (universal visibility); enforces gates only for agent PRs
- Required status check `booty/verifier` via GitHub Checks API
- Tests run in clean env; PR blocked if red
- Diff limits: max_files_changed, max_diff_loc, max_loc_per_file
- .booty.yml schema v1 validation
- Import/compile failure detection with annotations

---
*Last updated: 2026-02-15 after v1.3 milestone start*
