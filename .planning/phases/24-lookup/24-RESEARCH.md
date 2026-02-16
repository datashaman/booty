# Phase 24: Lookup - Research

**Researched:** 2026-02-16
**Domain:** Deterministic query engine on JSONL; path/fingerprint matching; Python stdlib
**Confidence:** HIGH

## Summary

Phase 24 delivers a lookup API that accepts a candidate change (paths, repo, head sha, optional fingerprint) and returns related memory records from the last 90 days. Matching is by path intersection OR fingerprint—deterministic, no embeddings. Performance target: <1s for 10k records.

CONTEXT.md from `/gsd:discuss-phase` locks implementation decisions: path matching (prefix/containment, weighted scoring), fingerprint additive with paths, result limits, severity canonical scale, tie-breaking rules. Research focuses on patterns and stdlib usage to implement those decisions.

**Primary recommendation:** Use stdlib only; pathlib.PurePosixPath for path normalization (GitHub paths are POSIX); single-pass read_records + in-memory filter + sorted(); severity via lookup dict for canonical order.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pathlib | stdlib | Path normalization | Cross-platform, PurePosixPath for repo paths |
| datetime | stdlib | Retention cutoff | 90-day filter via fromisoformat |
| operator | stdlib | Multi-key sort | itemgetter for tuple keys |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| store.read_records | Load memory.jsonl | Single source of records |
| datetime.fromisoformat | Parse record timestamps | Retention filtering |

**Installation:** None — stdlib only.

## Architecture Patterns

### Recommended Project Structure
```
src/booty/memory/
├── lookup.py      # query(...) API
├── store.py       # existing read_records
├── config.py      # MemoryConfig.retention_days, max_matches
└── api.py         # existing add_record
```

### Pattern 1: Path Normalization for Repo Paths
**What:** Normalize paths to consistent form before comparison. GitHub/repo paths use forward slashes.
**When to use:** Every path comparison in lookup.
**Example:**
```python
from pathlib import PurePosixPath

def normalize_path(p: str) -> str:
    """Normalize: strip, collapse slashes, remove ./ prefix."""
    if not p or not isinstance(p, str):
        return ""
    s = p.strip().replace("\\", "/").lstrip("./")
    return str(PurePosixPath(s)) if s else ""
```

### Pattern 2: Path Prefix/Containment Match
**What:** Record path matches candidate if either is prefix of the other.
**When to use:** Path intersection scoring per CONTEXT.
**Example:**
```python
def path_matches(cand: str, rec_path: str) -> int:
    """Return 2 if exact match, 1 if prefix match, 0 else."""
    cn, rn = normalize_path(cand), normalize_path(rec_path)
    if not cn or not rn:
        return 0
    if cn == rn:
        return 2
    if rn.startswith(cn + "/") or cn.startswith(rn + "/"):
        return 1
    return 0
```

### Pattern 3: Multi-Key Sort with Custom Order
**What:** Sort by severity (custom order), recency desc, path_overlap desc, id asc.
**When to use:** Result ordering per MEM-17.
**Example:**
```python
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}

def sort_key(rec: dict) -> tuple:
    sev = SEVERITY_ORDER.get((rec.get("severity") or "").lower(), 4)
    ts = rec.get("timestamp") or ""
    return (sev, -parse_ts(ts), -rec.get("path_overlap", 0), rec.get("id", ""))
```

### Anti-Patterns to Avoid
- **Don't use Path.resolve() for repo paths** — resolve() needs filesystem; repo paths are logical strings.
- **Don't sort multiple times** — one sorted() with tuple key is correct and fast for 10k records.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path normalization | Regex / manual split | PurePosixPath + str | Handles slashes, edge cases |
| Timestamp parsing | Custom parser | datetime.fromisoformat | ISO8601 support |
| Multi-key sort | Multiple .sort() | sorted(..., key=tuple) | Single pass, correct tie-breaking |

## Common Pitfalls

### Pitfall 1: Severity Case Sensitivity
**What goes wrong:** "High" vs "high" break ordering.
**Why it happens:** Different sources use different casing.
**How to avoid:** Normalize to lowercase before lookup: `(rec.get("severity") or "").lower()`.
**Warning signs:** Results not ordered by severity.

### Pitfall 2: Empty paths/fingerprint
**What goes wrong:** Match everything or nothing when candidate paths=[].
**Why it happens:** Empty list still iterates in some logic.
**How to avoid:** Short-circuit: if not paths and not fingerprint → return []; if paths → path match only; if fingerprint → fingerprint match only; combine with OR.
**Warning signs:** Unexpected empty or full result sets.

### Pitfall 3: Retention Boundary
**What goes wrong:** Off-by-one at 90-day boundary.
**Why it happens:** Timezone or inclusive vs exclusive cutoff.
**How to avoid:** `cutoff = now - timedelta(days=retention_days)`; record passes if `record_ts >= cutoff` (inclusive of boundary).
**Warning signs:** Records missing at exactly 90 days.

## Code Examples

### Retention Filter
```python
from datetime import datetime, timedelta, timezone

def within_retention(record: dict, retention_days: int) -> bool:
    ts = record.get("timestamp")
    if not ts:
        return False
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        return dt >= cutoff
    except (ValueError, TypeError):
        return False
```

### Repo Filter
```python
def repo_matches(record: dict, repo: str | None) -> bool:
    if not repo:
        return True
    return (record.get("repo") or "").strip() == repo.strip()
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| SQL/DB for JSONL | In-memory filter + sort | No new deps; 10k records trivial |
| Regex path match | PurePosixPath normalization | Consistent, cross-platform |

## Open Questions

1. **Paths hash for verifier_cluster fingerprint**
   - What we know: Verifier builds fingerprint from sorted paths hash (adapters.py).
   - What's unclear: Whether lookup needs to derive paths_hash from candidate paths for fingerprint match. CONTEXT says "derive paths_hash from candidate paths to match verifier_cluster fingerprints when caller has paths." Recommendation: Implement in lookup—hash sorted candidate paths, match against record fingerprints prefixed with `import:` or `compile:` or `test:`.
   - Recommendation: Add helper to derive paths_hash; use in fingerprint match when fingerprint not provided but paths are.

## Sources

### Primary (HIGH confidence)
- Python 3 pathlib docs — path normalization, PurePosixPath
- Python 3 datetime — fromisoformat, timedelta
- CONTEXT.md — locked implementation decisions

### Secondary (MEDIUM confidence)
- WebSearch: Python path normalization, multi-key sort (verified patterns)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, no new deps
- Architecture: HIGH — CONTEXT.md provides rules; patterns verified
- Pitfalls: HIGH — common issues documented

**Research date:** 2026-02-16
**Valid until:** 30 days (stable domain)
