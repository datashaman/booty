# Phase 42: Event Router — Research

## RESEARCH COMPLETE

**Gathered:** 2026-02-17
**Status:** Ready for planning

---

## Executive Summary

The webhook handler (`webhooks.py`) currently routes events inline across ~700 lines. Five event families (issues, pull_request, workflow_run, check_run, push) each implement ad-hoc enablement checks and enqueue logic. Phase 42 extracts a canonical router, normalizes GitHub payloads to internal events, and introduces a single `should_run(agent, repo, context)` decision point.

---

## Current State

### Event Handling Locations
- **`webhooks.py`** — Single entry `/webhooks/github`; branches on `event_type` (check_run, pull_request, workflow_run, push, issues)
- **Enablement checks** — Scattered: `planner_enabled()`, `verifier_enabled()`, `security_enabled()`; Reviewer inferred from Verifier (same App)
- **No Reviewer enablement at routing** — Reviewer uses `verifier_enabled()`; per-repo Reviewer config (e.g. `block_on`) loaded later in runner

### Per-Event Routing Today

| Event         | Actions          | Agents Enqueued                         | Enablement Source                    |
|---------------|------------------|-----------------------------------------|--------------------------------------|
| issues        | opened, labeled  | Planner, Builder                        | planner_enabled, job_queue presence |
| pull_request  | opened, sync, re | Verifier, Security, Reviewer (agent PRs) | verifier_enabled, security_enabled   |
| workflow_run  | completed        | Governor (evaluate / observe_deploy)    | governor_config.enabled from .booty   |
| check_run     | completed        | Memory surfacing only                   | mem_config.enabled                   |
| push          | (main)           | Revert detection → Memory ingestion     | mem_config.enabled                   |

### Queue Dedup Signatures
- **VerifierQueue** — `is_duplicate(pr_number, head_sha)`, `mark_processed(pr_number, head_sha)` — no repo (DEDUP-04 Phase 43)
- **SecurityQueue** — same
- **ReviewerQueue** — `is_duplicate(repo_full_name, pr_number, head_sha)` — already has repo
- **Planner** — `planner_is_duplicate(delivery_id)`, `planner_mark_processed(delivery_id)`
- **Builder (JobQueue)** — `is_duplicate(delivery_id)`, `has_issue_in_queue(repo_url, issue_number)`

---

## Key Findings

### 1. Internal Event Shapes (from 42-CONTEXT)
- Event-type-specific structs with `raw_payload`
- Typed families: `IssueEvent`, `PREvent`, `WorkflowRunEvent`
- Shared routing fields: `action`, `issue_number`/`pr_number`, `head_sha`, `workflow_run` id/name/conclusion, `sender`, `delivery_id`

### 2. should_run Precedence
- **Layer 1:** `enabled(agent)` — global enablement (env/file)
- **Layer 2:** `should_run(agent, ctx)` — routing/gating (e.g. is_agent_pr for Reviewer)
- Precedence: Env > File > Default
- Per-agent defaults when file absent (Planner/Builder drivers; Verifier/Security rails; Architect/Reviewer optional)

### 3. Reviewer Enablement Gap
- Today: `reviewer_ok = reviewer_queue and verifier_enabled(settings)` — no per-repo Reviewer config at route time
- ReviewerConfig.enabled + block_on loaded in runner
- ROUTE-03 says "per agent config" — Phase 42 can defer per-repo Reviewer enablement to runner; routing uses global Reviewer-on (when Verifier App present) and `is_agent_pr` gating

### 4. Governor workflow_run Routing
- Two paths: deploy outcome (observe) vs verification success (evaluate → decision)
- Identity: `deploy_workflow_name`, `verification_workflow_name` from governor config
- ROUTE-04 satisfied if router normalizes workflow_run → `governor.evaluate` or `governor.observe_deploy` internal event

### 5. Incremental Migration
- Keep current job payload shapes; internal events for routing + dedup key derivation only
- Flip enqueue paths one-by-one

---

## Implementation Risks

1. **Scope creep** — Architect/Builder wiring (Phase 44) lives in issues branch; Phase 42 extracts router but leaves Planner→Architect→Builder flow intact
2. **Reviewer per-repo** — ROUTE-03 "per agent config" could mean per-repo; 42-CONTEXT says "enablement vs routing/gating" — keep enablement at route, gating (e.g. block_on) in runner
3. **Operator observability (ROUTE-01)** — "observe" = logs, structure, or endpoint; minimal structured skip logging acceptable; full OPS-01 in Phase 47

---

## Recommendations for Planning

1. **Extract `src/booty/router/`** — `events.py` (internal event structs), `normalizer.py` (GitHub → internal), `should_run.py` (decision), `router.py` (orchestration)
2. **Single dispatch entry** — Webhook parses, calls router with (event_type, payload, headers); router normalizes, decides, enqueues
3. **Config loader** — Router needs access to settings + booty_config for agent enablement; reuse `_load_booty_config_for_repo`
4. **Dedup key derivation** — Router computes keys (repo, pr_number, head_sha) for PR agents; pass to enqueue; queue signatures unchanged in Phase 42 (Phase 43 adds repo to Verifier/Security)

---

## Open Decisions (Claude's Discretion)
- Global kill switch env name (e.g. `BOOTY_DISABLED` or `AGENTS_DISABLED`)
- Minimal skip observability now vs defer to Phase 47
