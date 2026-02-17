# Phase 41: Fail-Open + Metrics - Research

**Researched:** 2026-02-17
**Domain:** Reviewer failure handling, persisted metrics, structured logging
**Confidence:** HIGH

## Summary

Phase 41 hardens Reviewer failure handling (fail-open REV-09), emits metrics and structured logs (REV-15), and adds minimal docs. All implementation decisions are locked in CONTEXT.md. The work extends established patterns from Architect (metrics, CLI) and Verifier (structured logging).

**Primary recommendation:** Mirror Architect metrics pattern exactly (events array, rolling 24h, tempfile atomic write). Use structlog (already in use) for structured logs with repo, pr, sha, outcome, blocked_categories, suggestion_count.

## Standard Stack

### Core (already in use)
| Component | Purpose | Source |
|-----------|---------|--------|
| booty.architect.metrics | events JSON, increment_*, get_24h_stats | src/booty/architect/metrics.py |
| structlog | Structured logging | queue.py, verifier/runner.py, main.py |
| get_planner_state_dir | Base state path | booty.planner.store |

### Path Conventions
| Path | Purpose |
|------|---------|
| state_dir/reviewer/metrics.json | Reviewer events (reviews_total, reviews_blocked, reviews_suggestions, reviewer_fail_open) |

## Architecture Patterns

### Metrics (mirror Architect)
- Events array: `{"events": [{"ts": iso, "type": "approved"|"blocked"|"suggestions"|"fail_open"}, ...]}`
- Rolling 24h window on read; prune optional
- Atomic write: tempfile + os.replace
- increment_reviews_total, increment_reviews_blocked, increment_reviews_suggestions, increment_reviewer_fail_open(fail_open_type: str)

### Fail-Open (CONTEXT)
- Check output only — no PR comment when fail-open triggers
- Title: "Reviewer unavailable (fail-open)"
- Summary: "Review did not run; promotion/merge not blocked"
- Bucket failures for metrics/logs: diff_fetch_failed, github_api_failed, llm_timeout, llm_error, schema_parse_failed, unexpected_exception

### Structured Logging (structlog)
- Pattern: `logger.info("event_name", repo=..., pr=..., sha=..., outcome=..., blocked_categories=..., suggestion_count=...)`
- On fail-open: include fail_open_type

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Metrics storage | Custom DB | architect/metrics pattern | Consistency, survives restarts |
| Log aggregation | Custom collector | structlog key-value | Already used; REV-15 requires structured logs |
| CLI status | New framework | Click group (architect pattern) | booty reviewer status --json |

## Common Pitfalls

### Pitfall 1: Fail-open PR comment
**What goes wrong:** Posting PR comment on fail-open.
**Why:** CONTEXT explicitly: "Check output only — no PR comment when fail-open triggers."
**How to avoid:** edit_check_run only; do NOT call post_reviewer_comment on fail-open.

### Pitfall 2: Status command reading logs
**What goes wrong:** booty reviewer status parsing log output.
**Why:** CONTEXT: "Do not depend on log aggregation for status (metrics must be persisted)."
**How to avoid:** get_reviewer_24h_stats() reads from metrics.json only.

## Code Examples

### Architect metrics pattern (copy structure)
```python
# From src/booty/architect/metrics.py
def _append_event(event_type: str, state_dir: Path | None = None) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    events = _load_events(state_dir)
    events.append({"ts": ts, "type": event_type})
    _save_events(events, state_dir)
```

### structlog in Reviewer (queue.py pattern)
```python
log = self._logger.bind(job_id=job.job_id, pr_number=job.pr_number)
log.info("reviewer_outcome", repo=..., sha=..., outcome=..., blocked_categories=[...])
```

## Open Questions

None — CONTEXT.md has locked all decisions.

## Sources

### Primary
- src/booty/architect/metrics.py — metrics pattern
- src/booty/reviewer/runner.py — current exception handling (lines 118-128)
- src/booty/cli.py — architect status command (lines 541-581)
- .planning/phases/41-fail-open-metrics/41-CONTEXT.md — locked decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing codebase patterns
- Architecture: HIGH — Architect/metrics + structlog established
- Pitfalls: HIGH — CONTEXT explicit

**Research date:** 2026-02-17
**Valid until:** 30 days (stable internal patterns)
