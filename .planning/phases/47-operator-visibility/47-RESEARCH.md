# Phase 47: Operator Visibility - Research

**Researched:** 2026-02-17
**Domain:** Structured logging, CLI status, observability
**Confidence:** HIGH

## Summary

Phase 47 adds operator visibility: structured skip logs when the router ignores events, and `booty status` CLI extensions (last_run_completed_at, queue_depth). OPS-01 through OPS-04. No new external dependencies; uses existing Python stdlib logging and CLI patterns.

The router already emits `event_skip` with agent, repo, event_type, reason. Phase 47 refines: (1) add `decision=skip` for OPS-01 consistency, (2) map reasons to five OPS-02 buckets, (3) use INFO for operator-actionable skips, DEBUG for high-volume. Verifier `promotion_waiting_reviewer` already exists; verify and document.

For `booty status`: extend existing key-value CLI. Queues expose `qsize()` (asyncio.Queue). Last-run timestamps: architect/reviewer use JSON metrics files; same pattern applies for agents without metrics.

**Primary recommendation:** Use stdlib logging (logger.info vs logger.debug). Extend status CLI with per-agent last_run_completed_at and queue_depth from queues or N/A. No new libraries.

## Standard Stack

### Core
| Component | Purpose | Why Standard |
|-----------|---------|--------------|
| Python stdlib `logging` | Structured skip logs | Already used; logger.info/debug with extra kwargs |
| Click | booty CLI | Already used; status command exists |
| asyncio.Queue | Queue depth | Already used; `.qsize()` available |

### No New Libraries
Phase 47 is internal observability. All required infrastructure exists.

## Architecture Patterns

### Skip Log Structure (OPS-01)
```
logger.info("event_skip", agent=..., repo=..., event_type=..., decision="skip", reason=..., _reason_raw=...)
```
- `decision="skip"` for OPS-01
- `reason` = five-bucket vocabulary (OPS-02)
- `_reason_raw` = original granular reason (debug-only; CONTEXT)

### INFO vs DEBUG (per 47-CONTEXT)
- **INFO:** disabled, missing_config, normalize_failed (operator-actionable)
- **DEBUG:** not_agent_pr, dedup_hit, expected routing misses

### booty status Layout (per 47-CONTEXT)
```
agent_name:
  enabled: true|false
  last_run_completed_at: ISO-8601 UTC | N/A
  queue_depth: int | N/A
```
Key-value style per agent. Add Builder, Reviewer. Use N/A when unknown.

### Last-Run Timestamp Source
Architect and Reviewer use JSON metrics files in state dir. Same pattern:
- Worker records completion event with ISO-8601 UTC timestamp on job completion
- CLI reads latest event timestamp
- Fallback: N/A when no events

### Queue Depth
- `VerifierQueue._queue.qsize()` — available
- `ReviewerQueue`, `SecurityQueue`, `JobQueue` — asyncio.Queue has `.qsize()`
- Architect/Planner/Builder — JobQueue or dedicated queues; check structure
- CLI needs app_state/queue references; status command may run without app — N/A when queues not available

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|--------|-------------|-------------|-----|
| Structured logs | Custom format | logger.info("event_skip", **kwargs) | Already used; grep-able |
| Timestamps | Custom serializer | datetime.now(timezone.utc).isoformat() | ISO-8601 per CONTEXT |
| Queue depth | Custom counter | queue.qsize() | stdlib |

## Common Pitfalls

### Pitfall 1: Log Level Misuse
**What goes wrong:** All skips at INFO floods logs
**Why it happens:** not_agent_pr and dedup_hit are high-volume
**How to avoid:** Per CONTEXT: INFO for operator-actionable; DEBUG for high-volume
**Warning signs:** Log volume spikes after Phase 47

### Pitfall 2: status Without App
**What goes wrong:** booty status needs app_state for queue_depth
**Why it happens:** status runs standalone, no queues
**How to avoid:** Use N/A when queue not available; don't require running app
**Warning signs:** status fails when app not running

### Pitfall 3: Reason Bucket Leakage
**What goes wrong:** New router reason not mapped to five buckets
**Why it happens:** New code paths add reasons
**How to avoid:** Map all reasons to five buckets; add _reason_raw for debugging
**Warning signs:** OPS-02 vocabulary violated

## Code Examples

### Skip Log with Bucket + Raw (router)
```python
# Map granular reason to five-bucket vocabulary
REASON_BUCKET = {
    "normalize_failed": "normalize_failed",
    "disabled": "disabled",
    "governor_disabled": "disabled",
    "all_pr_agents_disabled": "disabled",
    "not_plan_or_builder_trigger": "not_agent_pr",
    "unhandled_action": "not_agent_pr",
    "workflow_not_completed": "not_agent_pr",
    "workflow_not_matched": "not_agent_pr",
    # ... etc
}
bucket = REASON_BUCKET.get(reason, "not_agent_pr")
log_fn = logger.info if bucket in ("disabled", "missing_config", "normalize_failed") else logger.debug
log_fn("event_skip", agent=..., repo=..., event_type=..., decision="skip", reason=bucket, _reason_raw=reason)
```

### booty status Extended Output
```python
# Per agent: enabled, last_run_completed_at, queue_depth
# last_run: from metrics store or N/A
# queue_depth: from app_state.verifier_queue._queue.qsize() if available else N/A
```

## Open Questions

1. **status and app_state:** booty status runs as CLI; app not started. Queue depth requires app_state. Recommendation: status accepts optional --app-url or reads from env if app exposes metrics; otherwise N/A. (Per CONTEXT: "Queue depth instrumentation approach when not yet available" — Claude's discretion.)

2. **Builder/Reviewer last_run:** Builder uses JobQueue; Reviewer has metrics. Architect/reviewer metrics pattern for last_run. Builder: job completion in main.py — add metrics write or use existing job completion log.

## Sources

### Primary (HIGH confidence)
- router.py — existing event_skip pattern, reason vocabulary
- cli.py — status command, architect status, reviewer status
- VerifierQueue, JobQueue — qsize() available
- architect/metrics.py — JSON metrics pattern

### Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps, stdlib only
- Architecture: HIGH — patterns exist in codebase
- Pitfalls: HIGH — CONTEXT provides clear decisions

**Research date:** 2026-02-17
**Valid until:** 30 days
