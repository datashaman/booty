# Phase 22: Memory Foundation - Research

**Researched:** 2026-02-16
**Domain:** Append-only JSONL storage, config extension, dedup, Python file I/O
**Confidence:** HIGH

## Summary

Phase 22 delivers the Memory Agent foundation: append-only `memory.jsonl` storage with atomic writes and fsync, stable schema for records, config block in .booty.yml with env overrides, and `memory.add_record(record)` API with 24h-window dedup. The codebase already has Governor store (`release_governor/store.py`) with atomic JSON writes, fcntl flock, and state dir resolution. BootyConfigV1 extends cleanly with optional blocks (security, release_governor). Standard approach: create `booty/memory/` module with store (append-only JSONL + flock), schema (MemoryRecord), config (MemoryConfig + env overrides), and add_record API. Use stdlib only; no new dependencies.

**Primary recommendation:** Use stdlib (fcntl, tempfile, json, os) for append-only JSONL; extend BootyConfigV1 with memory block; validate memory config lazily so unknown keys fail Memory only without breaking other agents; reuse state-dir pattern (MEMORY_STATE_DIR or shared).

## Standard Stack

### Core
| Library | Purpose | Why Standard |
|---------|---------|--------------|
| Python stdlib (fcntl, json, os, pathlib) | Append + flock + fsync | No new deps; Governor store proves pattern |
| Pydantic v2 | MemoryRecord schema, MemoryConfig | Already in project; ConfigDict(extra="forbid") for strict |
| PyYAML | .booty.yml | Already used |
| uuid | Record IDs | Stdlib; uuid.uuid4() for unique ids |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| pathlib.Path | State dir, file paths | Consistent with store.py |
| structlog | Logging | Project standard |
| datetime (timezone.utc) | Timestamps | ISO8601 per schema |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Stdlib append + flock | atomicwrites, jsonlines | Stdlib sufficient; no new deps; project precedent |
| Single memory.jsonl | SQLite, LMDB | Spec requires append-only JSONL; keep simple |
| Inline config validation | Lazy validation in Memory module | Lazy allows "fail Memory only" per CONTEXT |

## Architecture Patterns

### Recommended Project Structure
```
src/booty/
├── memory/
│   ├── __init__.py      # add_record, get_memory_config
│   ├── config.py        # MemoryConfig, apply_memory_env_overrides
│   ├── schema.py        # MemoryRecord, common fields
│   └── store.py         # append_record, read_records, get_state_dir, dedup
├── test_runner/config.py  # Extend BootyConfigV1 with memory: dict | None (raw)
```

### Pattern 1: Append-Only JSONL with fsync
**What:** Open file in append mode, acquire LOCK_EX, write one JSON line + newline, flush, fsync, release.
**When to use:** Durable append-only event log.
**Example:**
```python
import fcntl
import json
import os

def append_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(json.dumps(record, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

### Pattern 2: Read Tolerating Partial Last Line
**What:** Iterate lines, try json.loads(line); skip line on JSONDecodeError (partial write).
**When to use:** Crash during append leaves partial line.
**Example:**
```python
def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # partial last line - skip
    return records
```

### Pattern 3: State Dir Resolution
**What:** Env MEMORY_STATE_DIR > $HOME/.booty/state > ./.booty/state. Create if missing.
**When to use:** Consistent with Governor; MEM-26 env overrides.
**Example:**
```python
def get_memory_state_dir() -> Path:
    if path := os.environ.get("MEMORY_STATE_DIR"):
        p = Path(path)
    elif home := os.environ.get("HOME"):
        p = Path(home) / ".booty" / "state"
    else:
        p = Path.cwd() / ".booty" / "state"
    p.mkdir(parents=True, exist_ok=True)
    return p
```

### Pattern 4: Config Validation — Fail Memory Only
**What:** BootyConfigV1.memory holds raw dict (no validation at parse). Memory module validates on use; ValidationError → raise MemoryConfigError with unknown key.
**When to use:** CONTEXT: "Parse together, fail separately."
**Example:**
```python
# In config: memory: dict | None (field_validator returns v as-is)
# In memory module:
def get_memory_config(booty_config) -> MemoryConfig | None:
    if booty_config.memory is None:
        return None
    try:
        return MemoryConfig.model_validate(booty_config.memory)
    except ValidationError as e:
        raise MemoryConfigError(f"Memory config invalid: {e}") from e
```

### Anti-Patterns to Avoid
- **Don't use read-modify-write for JSONL:** Governor pattern rewrites whole file; Memory is append-only.
- **Don't add jsonlines/atomicwrites:** Stdlib sufficient; project avoids new deps.
- **Don't validate memory block in BootyConfigV1 parse:** That would fail whole config on unknown keys; use lazy validation.
- **Don't forget fsync:** MEM-02 requires durable writes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config schema | Custom validation | Pydantic MemoryConfig + extra="forbid" | Unknown keys, type safety |
| Env overrides | Manual mapping | apply_memory_env_overrides (mirror Security) | MEMORY_ENABLED, MEMORY_RETENTION_DAYS, etc. |
| Record IDs | Custom ID generator | uuid.uuid4() | Stdlib, collision-free |
| Dedup key hash | Custom hashing | Tuple of (type, repo, sha, fingerprint, pr_number) | Simple, exclude None/empty per CONTEXT |

## Common Pitfalls

### Pitfall 1: Dedup key with null/empty fields
**What goes wrong:** Dedup matches on fingerprint when record has fingerprint=None, creating spurious duplicates.
**Why it happens:** CONTEXT says exclude null/empty from key — only match on present fields.
**How to avoid:** Build dedup key dict with only non-None, non-empty values; normalize to comparable tuple.
**Warning signs:** All records deduplicated incorrectly.

### Pitfall 2: 24h window semantics
**What goes wrong:** Window "anchored on first record" — later duplicates within 24h of first are ignored.
**Why it happens:** Keep-first semantics per CONTEXT.
**How to avoid:** When checking duplicate, find existing record by key; if exists and (now - existing.timestamp) < 24h, return duplicate.
**Warning signs:** Second write succeeds when it should be duplicate.

### Pitfall 3: Compaction during read
**What goes wrong:** Compaction moves records to archive while another process reads — partial read.
**Why it happens:** No cross-process coordination for compaction.
**How to avoid:** Compaction runs under LOCK_EX; readers use LOCK_SH; or compaction is single-threaded/scheduled when idle. Phase 22 can defer compaction to later; MEM-04 says "may be compacted."
**Warning signs:** Missing records after compaction.

### Pitfall 4: add_record when disabled
**What goes wrong:** Persist when memory.enabled=False.
**Why it happens:** Forgetting to check.
**How to avoid:** add_record checks config.enabled; if False, return `{ added: true, id: None }` (or no-op success) — idempotent, no persist.
**Warning signs:** Records in memory.jsonl when disabled.

## Code Examples

### add_record API shape
```python
def add_record(
    record: MemoryRecord,
    config: MemoryConfig,
    state_dir: Path,
) -> dict:
    """Return { added: True, id: str } or { added: False, reason: "duplicate", existing_id: str }."""
    if not config.enabled:
        return {"added": True, "id": None}
    key = _dedup_key(record)
    existing = _find_duplicate(state_dir, key, within_hours=24)
    if existing:
        return {"added": False, "reason": "duplicate", "existing_id": existing["id"]}
    record_id = str(uuid.uuid4())
    record["id"] = record_id
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    _append_record(state_dir / "memory.jsonl", record)
    return {"added": True, "id": record_id}
```

### MemoryRecord schema (MEM-03)
```python
class MemoryRecord(TypedDict, total=False):
    id: str
    type: str
    timestamp: str
    repo: str
    sha: str
    pr_number: int | None
    source: str
    severity: str
    fingerprint: str | None
    title: str
    summary: str
    paths: list[str]
    links: list[str]
    metadata: dict
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Whole-file rewrite for append | Append-only with fsync | No rewrite; crash-safe |
| Validate all blocks at parse | Lazy validation for Memory | Fail Memory only |
| Separate state dir per agent | MEMORY_STATE_DIR or shared .booty/state | Flexibility; consistent |

## Open Questions

1. **Shared vs dedicated state dir**  
   Governor uses RELEASE_GOVERNOR_STATE_DIR. Memory could use MEMORY_STATE_DIR or share .booty/state. Recommendation: MEMORY_STATE_DIR with fallback to same as Governor ($HOME/.booty/state) for single-machine setups.

2. **Compaction in Phase 22**  
   MEM-04 says retention + compaction. Phase scope includes retention config; compaction can be minimal (threshold-triggered) or deferred. Recommendation: Implement basic compaction (move old records to memory-archived.jsonl) when record count or age exceeds threshold; exact values at Claude's discretion.

## Sources

### Primary (HIGH confidence)
- Existing code: `src/booty/release_governor/store.py` — atomic write, flock, state dir
- Existing code: `src/booty/test_runner/config.py` — BootyConfigV1, SecurityConfig, env overrides
- CONTEXT.md — dedup, config, unknown-key semantics

### Secondary (MEDIUM confidence)
- Web search: Python append JSONL atomic fsync — stdlib pattern confirmed
- Phase 14 RESEARCH — Governor config/store patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all from existing codebase
- Architecture: HIGH — patterns proven in Governor/Security
- Pitfalls: HIGH — CONTEXT and MEM reqs are explicit

**Research date:** 2026-02-16
**Valid until:** ~30 days
