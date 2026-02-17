# Phase 35: Idempotency - Research

**Researched:** 2026-02-17
**Domain:** Architect plan cache, TTL semantics, comment diff
**Confidence:** HIGH

## Summary

Phase 35 adds idempotency to the Architect agent: cache approved/blocked outcomes by plan_hash, reuse within 24h TTL, and update the plan comment only when the booty-architect block would change.

The codebase already has a complete reference implementation in the Planner (Phase 31): `booty.planner.cache` with `plan_hash`, `is_plan_fresh`, TTL from `created_at`, env `PLANNER_CACHE_TTL_HOURS`. Architect should mirror these patterns, using `plan_hash` from the planner module (same Plan schema), `ARCHITECT_CACHE_TTL_HOURS` env, and a new cache layer for Architect results keyed by (owner, repo, issue_number, plan_hash).

Comment update policy: compute the architect section we would post, extract the existing `<!-- booty-architect -->` block from the plan comment, compare. Update only if different. This avoids churn and satisfies ARCH-25.

**Primary recommendation:** Reuse `booty.planner.cache.plan_hash` and `is_plan_fresh`; add `booty.architect.cache` with `find_cached_architect_result`, `save_architect_result`; add diff-before-update wrapper for `update_plan_comment_with_architect_section`.

## Standard Stack

### Core (already in use)
| Component | Purpose | Why Standard |
|-----------|---------|---------------|
| `hashlib.sha256` | plan_hash | stdlib, deterministic |
| `json.dumps(..., sort_keys=True, separators=(",", ":"))` | Canonical JSON | Planner pattern, stable hash |
| `datetime` (UTC) | TTL, created_at | Phase 31 pattern |
| `pathlib.Path` | Cache storage | Consistent with Planner/Memory |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| plan_hash from planner.cache | New architect-specific hash | Same Plan schema; reusing avoids drift |
| File-based cache | Redis/SQLite | Phase 31 uses files; consistency wins |
| Exact string diff | Normalized comparison | Exact string sufficient for HTML blocks |

## Architecture Patterns

### Planner Cache Reference (Phase 31)

```
booty/planner/cache.py:
  - plan_hash(plan: Plan) -> str     # Excludes metadata (created_at, input_hash, plan_hash)
  - _plan_content_for_hash(plan)    # plan.model_dump(), pop metadata
  - is_plan_fresh(created_at, ttl_hours) -> bool
  - find_cached_issue_plan(owner, repo, issue, input_hash, ttl) -> Plan | None
  - TTL: os.environ.get("PLANNER_CACHE_TTL_HOURS", "24")
```

### Architect Cache Layout

```
~/.booty/state/architect/{owner}/{repo}/{issue_number}/{plan_hash}.json
```

Single file per (owner, repo, issue, plan_hash). Content:

```json
{
  "created_at": "2026-02-17T12:00:00+00:00",
  "approved": true,
  "architect_plan": { "plan_version": "1", "goal": "...", ... },
  "block_reason": null
}
```

Or for blocked: `approved: false`, `block_reason: "..."`, `architect_plan: null`.

### Comment Diff Strategy

1. Compute `architect_section = format_architect_section(status, ...)` (what we would post).
2. Fetch plan comment body (already available or via GitHub API).
3. Extract existing block: `re.search(r"<!-- booty-architect -->.*?<!-- /booty-architect -->", body, re.DOTALL)`.
4. Compare: `existing_block == architect_section` (exact string).
5. If same: skip `update_plan_comment_with_architect_section`.
6. If different or missing: call `update_plan_comment_with_architect_section`.

`update_plan_comment_with_architect_section` in `github/comments.py` already replaces or inserts. We add a wrapper that does the fetch + diff first.

### Anti-Patterns to Avoid

- **Hash scope drift:** Do not invent new exclusions. Use `plan_hash` from planner.cache; Plan schema is shared.
- **Comment churn:** Always diff before update. ARCH-25 explicitly requires this.
- **Blocked-plan re-validation:** On cache hit (blocked), return immediately; do not re-run validation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Deterministic hash | Custom serialization | `plan_hash(plan)` from planner.cache | Phase 31 alignment, single source |
| TTL check | Custom date logic | `is_plan_fresh(created_at, ttl)` from planner.cache | Same semantics, tested |
| Atomic file write | Manual open/write | `tempfile.NamedTemporaryFile` + `os.replace` | Planner/store pattern |

## Common Pitfalls

### Pitfall 1: Hash input scope
**What goes wrong:** Including metadata in hash causes cache miss when only created_at changes.
**Why it happens:** Plan has `metadata` dict with created_at, input_hash, plan_hash.
**How to avoid:** Use `_plan_content_for_hash` pattern — `plan.model_dump()`, pop metadata.
**Warning signs:** Cache hits rarely; same plan generates different hashes.

### Pitfall 2: Comment update without diff
**What goes wrong:** Every cache hit triggers comment edit; GitHub rate limits or noisy history.
**Why it happens:** Cached result is identical to existing; we overwrite anyway.
**How to avoid:** Extract existing block, compare with computed section, update only if different.
**Warning signs:** Repeated identical edits in issue comment history.

### Pitfall 3: Blocked-plan re-validation
**What goes wrong:** Same plan blocked again runs full validation pipeline.
**Why it happens:** Cache lookup only for approved path.
**How to avoid:** Cache both approved and blocked outcomes; short-circuit on cache hit for both.
**Warning signs:** Blocked plans taking full validation time on retry.

## Code Examples

### plan_hash (reuse from planner.cache)
```python
# booty/planner/cache.py — already exists
def plan_hash(plan: Plan) -> str:
    canon = json.dumps(
        _plan_content_for_hash(plan), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canon.encode()).hexdigest()
```

### Architect cache lookup (new)
```python
# booty/architect/cache.py (new)
def find_cached_architect_result(
    owner: str, repo: str, issue_number: int,
    plan_hash_val: str,
    ttl_hours: float | None = None,
    state_dir: Path | None = None,
) -> ArchitectCacheEntry | None:
    ttl = ttl_hours or float(os.environ.get("ARCHITECT_CACHE_TTL_HOURS", "24"))
    path = _architect_cache_path(owner, repo, issue_number, plan_hash_val, state_dir)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    created_str = data.get("created_at")
    if not created_str:
        return None
    created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
    if not is_plan_fresh(created, ttl):  # from planner.cache
        return None
    return ArchitectCacheEntry(**data)
```

### Diff-before-update (new helper)
```python
# In github/comments.py or architect/output.py
def update_plan_comment_with_architect_section_if_changed(
    github_token: str, repo_url: str, issue_number: int,
    architect_section: str,
) -> bool:
    """Update only if booty-architect block differs. Returns True if updated."""
    body = _get_plan_comment_body(github_token, repo_url, issue_number)
    if not body:
        return False
    match = re.search(r"<!-- booty-architect -->.*?<!-- /booty-architect -->", body, re.DOTALL)
    existing = match.group(0) if match else None
    if existing == architect_section:
        return False  # No update needed
    return update_plan_comment_with_architect_section(
        github_token, repo_url, issue_number, architect_section
    )
```

## State of the Art

| Approach | Current | When | Impact |
|----------|---------|------|--------|
| Planner cache | input_hash + plan_path, TTL from created_at | Phase 31 | Architect mirrors with plan_hash |
| Comment update | Always replace block | Phase 34 | Phase 35 adds diff-first |
| Cache storage | Planner: plans/owner/repo/issue.json | Phase 27 | Architect: architect/owner/repo/issue/plan_hash.json |

## Open Questions

1. **Existing block fetch:** `update_plan_comment_with_architect_section` iterates comments and edits in place. For diff, we need the current body. Options: (a) Add `get_plan_comment_body` that returns body of comment containing `<!-- booty-plan -->`; (b) Pass current body from caller (main.py already has context). Recommendation: main.py has access to Planner result and we could load from GitHub when needed. Prefer (a) — keep diff logic self-contained.

2. **ARCHITECT_STATE_DIR vs shared state:** Planner uses PLANNER_STATE_DIR; Architect could use ARCHITECT_STATE_DIR or share base (~/.booty/state). CONTEXT defers to Claude. Recommendation: Use same base (get_planner_state_dir or get_state_dir) with architect/ subdir — consistency with existing layout.

## Sources

### Primary (HIGH confidence)
- `src/booty/planner/cache.py` — plan_hash, is_plan_fresh, find_cached_issue_plan
- `src/booty/planner/store.py` — get_planner_state_dir, plan_path_for_issue
- `src/booty/architect/output.py` — format_architect_section, build_architect_plan
- `src/booty/github/comments.py` — update_plan_comment_with_architect_section
- `src/booty/main.py` — Architect flow in _planner_worker_loop
- `.planning/phases/31-idempotency/` — Phase 31 plans and context

### Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Planner implementation is authoritative
- Architecture: HIGH — Patterns extracted from codebase
- Pitfalls: HIGH — Derived from Phase 31 and CONTEXT decisions

**Research date:** 2026-02-17
**Valid until:** 30 days (stable domain)
