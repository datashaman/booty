# Phase 31: Idempotency - Research

**Researched:** 2026-02-16
**Domain:** Content-addressable cache, plan deduplication, TTL semantics
**Confidence:** HIGH

## Summary

Phase 31 adds idempotency: same plan for unchanged inputs within 24h, with plan_hash for dedup. CONTEXT.md locks most decisions (input scope, TTL semantics, cache hit UX). This research focuses on implementation patterns and pitfalls.

**Key findings:**
- Python `hashlib.sha256` + canonical JSON (`json.dumps(..., sort_keys=True)` + compact whitespace) is the standard for content-addressable hashing
- TTL: use `datetime.now(timezone.utc)` and `timedelta(hours=N)`; store `created_at` in plan metadata for cache validation
- No external cache library needed — file-based storage matches existing planner/store.py patterns
- plan_hash: hash the normalized plan content (goal, steps, touch_paths, handoff, etc.) excluding metadata (created_at, issue_url)

**Primary recommendation:** Implement `input_hash` (canonical PlannerInput) and `plan_hash` (canonical Plan minus metadata) with Python stdlib; add `load_plan` and cache lookup before `generate_plan` in worker/CLI.

## Standard Stack

### Core (already in use)
| Library | Purpose | Why Standard |
|---------|---------|--------------|
| hashlib | Input/plan hashing | stdlib, SHA-256 deterministic |
| json | Canonical serialization | stdlib, sort_keys for stability |
| pathlib | Path resolution | stdlib, already used in store.py |
| datetime | TTL comparison | stdlib, UTC-aware timestamps |

### Don't Add
| Problem | Don't Build | Why |
|---------|-------------|-----|
| Cache layer | Redis, diskcache | CONTEXT: file-based, same as store.py; no new deps |
| TTL logic | Custom grace period | CONTEXT: "use until exactly TTL; no grace period" |

## Architecture Patterns

### Input Hash Canonical Form

Per CONTEXT: goal + body + labels (sorted) + source_type + incident_fields + default_branch (from repo_context). Exclude metadata (repo, issue_url, issue_number), tree.

```python
def _canonical_input(inp: PlannerInput) -> dict:
    """Build dict for hashing; exclude metadata."""
    d = {
        "goal": inp.goal.strip(),
        "body": inp.body.strip(),
        "labels": sorted(inp.labels),
        "source_type": inp.source_type,
    }
    if inp.incident_fields:
        d["incident_fields"] = dict(sorted(inp.incident_fields.items()))
    if inp.repo_context and "default_branch" in inp.repo_context:
        d["default_branch"] = inp.repo_context["default_branch"]
    return d

def input_hash(inp: PlannerInput) -> str:
    canon = json.dumps(_canonical_input(inp), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()
```

**Whitespace:** Strip goal/body; JSON `separators=(",", ":")` for compact, deterministic output.

**Labels:** `sorted(labels)` for determinism.

### plan_hash Canonical Form

Hash plan content excluding metadata that changes per run (created_at, etc.).

```python
def _plan_content_for_hash(plan: Plan) -> dict:
    """Fields included in plan_hash — excludes created_at, metadata."""
    d = plan.model_dump()
    d.pop("created_at", None)
    d.pop("metadata", None)
    # any other run-specific fields
    return d

def plan_hash(plan: Plan) -> str:
    canon = json.dumps(_plan_content_for_hash(plan), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()
```

### TTL Check (UTC, Sliding Window)

```python
from datetime import datetime, timezone, timedelta

def is_plan_fresh(created_at: datetime, ttl_hours: float = 24) -> bool:
    """True if plan is within TTL. created_at must be UTC-aware."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=ttl_hours)
    return created_at >= cutoff
```

Store `created_at` in plan JSON (ISO 8601); parse with `datetime.fromisoformat()` when loading.

### Ad-hoc Hash Index

CONTEXT: Lookup key = hash of canonical input + optional repo context. Keep timestamped paths; lookup via hash index.

**Structure:**
- `plans/ad-hoc/` directory
- `index.json`: `{"<input_hash>": "<filename>"}` mapping
- Files: `ad-hoc-<ts>-<hash>.json` (preserves history)

Lookup: compute input_hash → check index → load file if exists and fresh.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Custom hash | MD5, adler32 | hashlib.sha256 — collision resistance |
| Naive datetime | datetime.now() without tz | datetime.now(timezone.utc) |
| Custom TTL | Grace period, fuzzy expiry | Exact TTL per CONTEXT |

## Common Pitfalls

### Pitfall 1: Timezone Naivety
**What goes wrong:** `created_at` stored or compared without timezone; DST or server local time causes wrong TTL.
**How to avoid:** Always use `datetime.now(timezone.utc)` and store ISO 8601 with 'Z' or +00:00.

### Pitfall 2: Hash Instability
**What goes wrong:** Different Python version or dict iteration order produces different hash for same input.
**How to avoid:** `json.dumps(..., sort_keys=True)`; never hash raw dict iteration.

### Pitfall 3: Metadata in plan_hash
**What goes wrong:** plan_hash includes created_at → every save produces new hash → no dedup.
**How to avoid:** Explicit exclude list for plan_hash (created_at, metadata, etc.).

### Pitfall 4: Ad-hoc Overwrite
**What goes wrong:** Same input from different runs overwrites previous file; history lost.
**How to avoid:** CONTEXT: timestamped paths, hash index for lookup; never overwrite.

## Code Examples

### Load Plan with Metadata Check

```python
def load_plan(path: Path) -> Plan | None:
    """Load plan from path. Returns None if file missing or invalid."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return Plan.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return None
```

### Cache Lookup (Issue)

```python
def find_cached_plan(
    owner: str, repo: str, issue_number: int,
    input_hash: str, ttl_hours: float
) -> Plan | None:
    path = plan_path_for_issue(owner, repo, issue_number)
    plan = load_plan(path)
    if not plan:
        return None
    # Stored input_hash in plan metadata at save time
    if plan.metadata.get("input_hash") != input_hash:
        return None
    created = datetime.fromisoformat(plan.metadata["created_at"])
    if not is_plan_fresh(created, ttl_hours):
        return None
    return plan
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| No cache, always LLM | Check cache before generate_plan | Cost + latency savings |
| Metadata in hash | Explicit exclude for plan_hash | Stable dedup |

## Open Questions

1. **Schema extension:** Plan model needs `metadata` dict (or similar) for `created_at`, `input_hash`, `plan_hash`. Current schema has no metadata field — add optional `metadata: dict = Field(default_factory=dict)` with extra="forbid" preserved for top-level (metadata is allowlisted).
2. **Ad-hoc index file locking:** Single index.json; concurrent ad-hoc runs could race. Low risk for CLI (single process). If worker runs parallel jobs, consider file lock or append-only log.

## Sources

### Primary (HIGH confidence)
- Python 3.12 docs: hashlib, json, datetime
- CONTEXT.md (locked decisions)
- Existing store.py, schema.py, input.py

### Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, no new deps
- Architecture: HIGH — CONTEXT constrains; patterns match existing codebase
- Pitfalls: HIGH — well-known datetime/hashing issues

**Research date:** 2026-02-16
**Valid until:** 30 days (stable domain)
