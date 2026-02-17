# Phase 36: Builder Handoff & CLI - Research

**Researched:** 2026-02-17
**Domain:** Architect artifact persistence, CLI extension, internal events/metrics
**Confidence:** HIGH

## Summary

Phase 36 extends existing Architect flow with: (1) persisted ArchitectPlan artifact for Builder consumption, (2) typed events for metrics/traceability, (3) Builder handoff (consume artifact first, retire agent:builder), (4) `booty architect status` and `booty architect review --issue N` CLI, (5) metrics: plans_reviewed, plans_rewritten, architect_blocks, cache_hits.

All infrastructure exists: planner/store.py (plan_path_for_issue, save_plan, get_plan_for_issue), architect/cache.py (save_architect_result, _architect_cache_path), cli.py (Click groups: memory, governor, plan), main.py (_planner_worker_loop), webhooks.py (Builder/Planner triggers). No new external libraries needed.

**Primary recommendation:** Use existing patterns (plan_path_for_issue layout, governor/memory CLI style, structured logging) — this is integration work within the codebase.

## Standard Stack

### Core (already in use)
| Component | Purpose | Why Standard |
|-----------|---------|--------------|
| Click | CLI framework | Already used; memory, governor, plan groups exist |
| planner/store | Plan paths, save/load | plan_path_for_issue → plans/owner/repo/{issue}.json |
| architect/cache | Architect cache | _architect_cache_path → architect/owner/repo/issue/plan_hash.json |

### Path Conventions (from codebase)
| Path | Purpose |
|------|---------|
| state_dir/plans/owner/repo/{issue}.json | Planner plan (Builder fallback) |
| state_dir/architect/owner/repo/issue/plan_hash.json | Architect cache (idempotency) |
| state_dir/plans/owner/repo/{issue}-architect.json | **NEW** — ArchitectPlan artifact (ARCH-26) |

**Key:** Cache is keyed by plan_hash for 24h reuse. Artifact is one per issue — latest approved ArchitectPlan for Builder consumption.

## Architecture Patterns

### Artifact vs Cache
- **Cache (existing):** architect/owner/repo/issue/plan_hash.json — per plan_hash, TTL 24h
- **Artifact (new):** plans/owner/repo/{issue}-architect.json — single file per issue, overwritten on each approval

### Builder Consumption Order (ARCH-28)
1. Try get_architect_plan_for_issue(owner, repo, issue) → ArchitectPlan
2. Fallback: get_plan_for_issue → Plan (mark "unreviewed by Architect" per CONTEXT)
3. Webhook: if Architect-approved plan exists for current Planner input hash → enqueue Builder; else enqueue Planner

### CLI Pattern (from memory, governor)
```python
@cli.group()
def architect() -> None:
    """Architect commands."""

@architect.command("status")
@click.option("--repo", ...)
@click.option("--json", "as_json", is_flag=True)
def architect_status(...): ...
```

### Metrics Persistence (CONTEXT)
- Under ~/.booty/state/architect/
- Rolling 24h from now
- Counters: plans_reviewed, plans_rewritten, architect_blocks, cache_hits

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Plan persistence | Custom JSON handling | planner/store save_plan pattern (tempfile + replace) | Atomicity, existing logic |
| CLI structure | New framework | Click groups (memory, governor) | Consistency |
| State dir | Hardcoded path | get_planner_state_dir / get_architect_cache_dir | Env override, portability |
| Metrics storage | Custom DB | JSON file + rolling window (like governor state) | Simplicity, survives restarts |

## Common Pitfalls

### Pitfall 1: Cache vs Artifact Path Confusion
**What goes wrong:** Builder reads cache path (plan_hash keyed) instead of artifact (issue-keyed).
**Why it happens:** Cache and artifact serve different purposes; same "architect result" concept.
**How to avoid:** Explicit artifact path: plans/owner/repo/{issue}-architect.json; Builder never reads cache.

### Pitfall 2: Webhook Still Triggering Builder from agent:builder
**What goes wrong:** ARCH-28 requires Builder to listen for Architect approval only; agent:builder retired.
**How to avoid:** Webhook: remove Builder trigger on agent label; only enqueue Builder when Architect-approved plan exists for issue's current Planner input hash, or when Planner worker completes (in-process).

### Pitfall 3: Metrics Not Surviving Restarts
**What goes wrong:** In-memory counters lost on restart; status shows 0.
**How to avoid:** Persist to ~/.booty/state/architect/ per CONTEXT; rolling 24h window in file.

## Code Examples

### Artifact Path (new)
```python
def architect_artifact_path(owner: str, repo: str, issue_number: int, state_dir: Path | None = None) -> Path:
    """Plans artifact: state_dir/plans/owner/repo/{issue}-architect.json."""
    sd = state_dir or get_planner_state_dir()
    return sd / "plans" / owner / repo / f"{issue_number}-architect.json"
```

### Builder Plan Resolution (conceptual)
```python
# In Builder path: try architect artifact first
arch_plan = load_architect_plan_for_issue(owner, repo, issue_number)
if arch_plan:
    return _analysis_from_architect_plan(arch_plan)
plan = get_plan_for_issue(owner, repo, issue_number, token)
if plan:
    return _analysis_from_plan(plan)  # Mark unreviewed by Architect
return None
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Builder triggers from agent:builder | Builder only from Architect approval or Planner→Architect→Builder | ARCH-28 |
| Planner plan only | ArchitectPlan artifact first, Planner fallback | ARCH-26, ARCH-28 |
| No Architect CLI | booty architect status \| review | ARCH-29, ARCH-30 |

## Open Questions

1. **Event emission:** planner.plan.approved vs architect.plan.approved — REQUIREMENTS say planner.plan.approved (ARCH-27); CONTEXT lists both. Recommendation: Use architect.plan.approved for Architect approvals; Planner already has its own completion.
2. **Metrics endpoint:** CONTEXT says "structured logs + metrics endpoint (Prometheus/OpenTelemetry-style)". If no /metrics route exists, start with structured logs only; add endpoint in future if needed.

## Sources

### Primary (HIGH confidence)
- src/booty/architect/cache.py — cache path, save_architect_result
- src/booty/planner/store.py — plan_path_for_issue, get_plan_for_issue
- src/booty/cli.py — memory, governor, plan groups
- src/booty/main.py — _planner_worker_loop, Architect approval flow
- src/booty/webhooks.py — Planner/Builder trigger branches

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components in codebase
- Architecture: HIGH — patterns established
- Pitfalls: HIGH — derived from phase scope and CONTEXT

**Research date:** 2026-02-17
**Valid until:** 30 days (stable internal integration)
