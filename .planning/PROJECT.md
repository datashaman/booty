# Booty

## What This Is

Booty is a self-managing software system built on AI agents. It starts with a Builder agent that picks up GitHub issues, writes code, runs tests, and opens PRs — against any configurable repo, including its own. More agents (Verifier, Planner, Architect, etc.) get added as the system evolves and the pain reveals what's needed next.

## Core Value

A Builder agent that can take a GitHub issue and produce a working PR with tested code — the foundation everything else builds on.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Builder agent picks up labeled GitHub issues via webhook
- [ ] Builder clones target repo fresh for each task
- [ ] Builder uses LLM (via magentic) to understand issue and produce code
- [ ] Builder runs tests against the generated code
- [ ] Builder opens a PR with the changes
- [ ] Target repo is configurable (not hardcoded)
- [ ] Builder can work on its own repo (self-management)
- [ ] Issue filtering via specific GitHub label (e.g. `agent:builder`)
- [ ] Webhook listener receives GitHub issue events

### Out of Scope

- Multi-agent coordination protocols — pain will reveal what's needed
- Planner/Architect/Verifier agents — future agents added incrementally
- Web UI or dashboard — CLI and GitHub are the interfaces
- Custom LLM fine-tuning — use off-the-shelf models via magentic
- Production deployment infrastructure — runs locally first

## Context

- Vision inspired by modeling a high-performing software org as specialized AI agents organized in control theory layers (strategic/tactical/reality loops)
- The ChatGPT analysis identified 11 agent roles; we're starting with just the Builder to avoid protocol/abstraction quicksand
- Magentic chosen for LLM abstraction — decorator-based, type-safe, multi-backend support
- Self-managing: Booty's first real test is building more of itself
- The minimum viable agent stack (Architect, Planner, Builder, Verifier, Observability) is the north star, but we get there by feeling the pain, not by planning it all upfront

## Constraints

- **LLM Abstraction**: Magentic — keeps agent code readable, supports multiple backends
- **Language**: Python — scripts + API calls, no heavy framework
- **Trigger**: GitHub webhooks — event-driven, not polling
- **Workspace**: Fresh clone per task — clean isolation, no stale state
- **Interface**: GitHub issues in, PRs out — no custom UI

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Start with Builder only | Avoid protocol/abstraction quicksand; let pain reveal what's needed | — Pending |
| Magentic for LLM abstraction | Decorator-based, type-safe, multi-backend; keeps agent code clean | — Pending |
| GitHub webhooks for triggering | Event-driven is cleaner than polling; integrates with existing workflow | — Pending |
| Fresh clone per task | Isolation prevents stale state leaking between tasks; simplicity over speed | — Pending |
| Label-based issue filtering | Not every issue should trigger a build; explicit opt-in via label | — Pending |

---
*Last updated: 2026-02-14 after initialization*
