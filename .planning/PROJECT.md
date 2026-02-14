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

### Active

(None yet — define with `/gsd:new-milestone`)

### Out of Scope

- Multi-agent coordination protocols — pain will reveal what's needed
- Planner/Architect/Verifier agents — future agents added incrementally
- Web UI or dashboard — CLI and GitHub are the interfaces
- Custom LLM fine-tuning — use off-the-shelf models via magentic
- Production deployment infrastructure — runs locally first

## Context

Shipped v1.0 with 3,012 LOC Python across 77 files.
Tech stack: FastAPI, magentic, PyGithub, structlog, Pydantic Settings.
All 17 requirements satisfied. 4 phases, 13 plans executed in a single day.
Self-modification capability active with protected paths and quality gates.

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

---
*Last updated: 2026-02-14 after v1.0 milestone*
