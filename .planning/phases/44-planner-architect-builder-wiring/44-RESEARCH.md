# Phase 44: Planner→Architect→Builder Wiring — Research

## RESEARCH COMPLETE

**Gathered:** 2026-02-17
**Status:** Ready for planning

---

## Executive Summary

Phase 44 corrects the issue-event routing order and adds an Architect standalone enqueue path from the webhook. The current router checks `should_run("planner")` first and enqueues Planner regardless of plan state — wrong. Correct flow: resolve plan state via `get_plan_for_builder`, then route Architect-approved → Builder, unreviewed → Architect, no plan → Planner. Architect currently runs only from the Planner worker loop; we need ArchitectJob, architect_queue, architect worker, and dedup by (repo, plan_hash). A compat flag gates Builder’s Planner-plan fallback per WIRE-04.

---

## Current State

### Router `_route_issues` (router.py)

**Current flow:**
1. `has_trigger_label` and `should_run("planner")` → enqueue Planner, return (always prefers Planner)
2. If not that path: `get_plan_for_builder`; if `architect_enabled` and `unreviewed` → `plan = None`
3. If `plan is None` → "safety net" enqueue Planner (or post_builder_blocked if planner disabled)
4. If `plan` exists → enqueue Builder

**Bugs:**
- Planner is tried first when `should_run(planner)`, ignoring plan state. WIRE-01/02/03 require plan-state-first routing.
- When `unreviewed`, code sets `plan = None` and falls through to safety net → enqueues Planner. WIRE-02 says enqueue Architect, not Planner.
- No Architect enqueue path from webhook.

### Architect Trigger Today

- **Source:** Planner worker loop only (main.py `_planner_worker_loop`)
- **Flow:** Planner completes → if Architect enabled and not cache hit → `process_architect_input` inline → on approval enqueue Builder
- **Gap:** When a plan already exists (e.g. from an earlier Planner run) and the user adds the trigger label, the webhook should enqueue Architect — there is no such path today.

### Builder Plan Consumption (artifact.py)

- `get_plan_for_builder` → Architect artifact first, then Planner plan
- **No compat flag:** always falls back to Planner plan. WIRE-04: fallback only when compat enabled.

### Dedup (Phase 43)

- Planner: `(repo, delivery_id)`
- Builder: `(repo, delivery_id)` issue-driven; `(repo, plan_hash)` plan-driven (Phase 44)
- Architect: TBD Phase 44 — use `(repo, plan_hash)` per 43-RESEARCH

---

## Requirements Mapping

| Req | Current | Gap |
|-----|---------|-----|
| WIRE-01 | Architect-approved → Builder | Router can reach Builder when approved; flow exists |
| WIRE-02 | Unreviewed → Architect | Router enqueues Planner, not Architect. No Architect enqueue. |
| WIRE-03 | No plan → Planner | Works when plan is None; order wrong (Planner checked first) |
| WIRE-04 | Builder Architect first, Planner only when compat | No compat flag; always Planner fallback |
| WIRE-05 | Auditable routing docs | No docs/routing.md; logic scattered |

---

## Key Findings

### 1. Plan-State-First Routing

Resolve plan before any enqueue:

```
plan, unreviewed = get_plan_for_builder(...)
architect_enabled = ...
compat = builder_compat_from_config()

if architect_enabled:
  if plan and not unreviewed:     → builder.enqueue
  elif plan and unreviewed:       → architect.enqueue
  else:                           → planner.enqueue
else:
  if plan:                        → builder.enqueue  (Architect skipped; compat allows Planner)
  else:                           → planner.enqueue
```

Remove the "Planner first when should_run(planner)" branch — routing is driven by plan state, not agent preference.

### 2. Architect Standalone Enqueue

- **ArchitectJob:** `job_id`, `issue_number`, `issue_url`, `repo_url`, `owner`, `repo`, `payload`, `plan_hash`
- **architect_queue:** `asyncio.Queue[ArchitectJob]` (like planner_queue)
- **architect_enqueue(job)**, **architect_is_duplicate(repo, plan_hash)**, **architect_mark_processed**
- **Architect worker loop:** pop job → load plan via `get_plan_for_issue` → `process_architect_input` → approve → save_artifact, enqueue Builder; block → post comment, add label

### 3. Compat Flag

- **Config:** `builder_compat` or `architect.builder_compat` in .booty.yml; env `BUILDER_COMPAT` / `ARCHITECT_BUILDER_COMPAT`
- **Default:** true (safe migration)
- **get_plan_for_builder:** when compat=false, if no Architect artifact return `(None, False)` — no Planner fallback
- **Routing:** compat only affects Builder consumption; when compat=false and unreviewed, route to Architect (Builder would get no plan)

### 4. Disabled-Agent Behavior (from 44-CONTEXT)

- Architect disabled + plan exists → Builder uses Planner plan (Architect skipped)
- Planner disabled + no plan → post builder_blocked, don't enqueue
- Planner disabled + Architect-approved plan → Builder only
- Architect disabled + unreviewed → Builder uses Planner plan (compat allows)

---

## Implementation Notes

### Architect Worker vs Planner Worker

Planner worker today runs Architect inline when plan is fresh. Two trigger sources:
1. **Planner completion** — keep inline in planner worker (no Architect enqueue)
2. **Webhook (existing unreviewed plan)** — new Architect enqueue + architect worker

Alternative: always enqueue Architect when Architect needed (both from Planner and webhook). That would require Planner worker to call architect_enqueue instead of running Architect inline — larger refactor. Simpler: keep Planner→Architect inline; add webhook→Architect enqueue path only.

### plan_hash for Dedup

Per Phase 43: Architect dedup `(repo, plan_hash)`. plan_hash = hash of plan JSON. Need to compute when enqueueing Architect from webhook — can use `get_plan_for_issue` + hash, or read from plan file if present.

---

## Files to Modify

| File | Change |
|------|--------|
| `src/booty/router/router.py` | Plan-state-first routing; Architect enqueue when unreviewed |
| `src/booty/architect/artifact.py` | get_plan_for_builder: respect compat flag |
| `src/booty/architect/config.py` | builder_compat in ArchitectConfig; env override |
| `src/booty/architect/jobs.py` | New: ArchitectJob, architect_queue, architect_enqueue, architect_is_duplicate |
| `src/booty/main.py` | Architect worker loop; ensure Builder gets jobs from Architect path |
| `docs/routing.md` | New: decision table, config precedence, disabled-agent matrix |
| `src/booty/planner/store.py` or artifact | plan_hash helper if needed for Architect dedup |

---

## Dependency Order

1. **Compat flag** — config + get_plan_for_builder (can be Wave 1)
2. **Architect jobs/queue/worker** — needed for webhook enqueue (Wave 1)
3. **Router rewrite** — plan-state-first, Architect enqueue (Wave 2, depends on 1–2)
4. **Documentation** — can parallel or Wave 2

---

*Phase: 44-planner-architect-builder-wiring*
*Research gathered: 2026-02-17*
