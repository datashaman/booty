# Phase 23: Ingestion - Research

**Researched:** 2026-02-16
**Domain:** Internal integration — wiring Booty agents into Memory
**Confidence:** HIGH

## Summary

Phase 23 wires six event sources (Observability, Governor HOLD, Governor deploy failure, Security FAIL/ESCALATE, Verifier FAIL, Revert) into `memory.add_record`. The API and schema exist (Phase 22). Each source produces a record dict matching MemoryRecord and calls `add_record(record, config, state_dir)`. Config comes from `get_memory_config(booty_config)` — each call site must load .booty.yml to obtain booty_config. Memory disabled → add_record is a no-op (returns `{added: True, id: None}`). Dedup is handled inside add_record. No new dependencies.

**Primary recommendation:** Create adapter functions `build_*_record(...)` in `booty/memory/adapters.py` that return record dicts; call `add_record` at each source's success/failure point. Use try/except around memory calls so ingestion never blocks primary agent flow.

## Standard Stack

### Core (Already in Project)
| Component | Purpose | Location |
|-----------|---------|----------|
| memory.add_record | Persist record with dedup | src/booty/memory/api.py |
| memory.get_memory_config | Validate memory config | src/booty/memory/config.py |
| MemoryRecord schema | type, timestamp, repo, sha, pr_number, source, severity, fingerprint, title, summary, paths, links, metadata | src/booty/memory/schema.py |

### Sources to Wire
| Source | Record Type | Call Site |
|--------|-------------|-----------|
| Observability | incident | webhooks.py sentry_webhook, after create_sentry_issue_with_retry returns issue_number |
| Governor HOLD | governor_hold | webhooks.py, after decision.outcome=="HOLD" and post_hold_status |
| Governor deploy | deploy_failure | webhooks.py, in is_deploy branch when conclusion in (failure, cancelled) |
| Security FAIL | security_block | security/runner.py, at each edit_check_run(conclusion="failure") |
| Security ESCALATE | security_block | security/runner.py, when persist_override + conclusion="success" |
| Verifier FAIL | verifier_cluster | verifier/runner.py, at each failure path (import, compile, install, test) |
| Revert | revert | New: push to main handler or CLI `booty memory ingest revert` |

### Config Loading
| Context | BootyConfig Source |
|---------|-------------------|
| webhooks.py (sentry, workflow_run) | Load .booty.yml from TARGET_REPO or repo default branch |
| security/runner.py | Already loads via get_verifier_repo + get_contents |
| verifier/runner.py | Already loads via load_booty_config or load_booty_config_from_content |
| failure_issues.py | No direct repo access — caller (webhooks) has gh_repo; config from webhooks flow |

**Key insight:** webhooks.py loads governor_config from .booty.yml for workflow_run; extend to also get booty_config (full) and pass memory_config where needed. Sentry webhook uses TARGET_REPO_URL — need to load .booty.yml from that repo's default branch.

## Architecture Patterns

### Adapter Pattern
**What:** Each source has a `build_X_record(...)` that returns a dict conforming to MemoryRecord. The caller builds the record, gets memory_config, and calls add_record. Adapters are pure functions; no side effects.

**When:** Any source producing a memory record.

**Example:**
```python
# booty/memory/adapters.py
def build_incident_record(event: dict, issue_number: int, repo: str) -> dict:
    """Build incident record from Sentry event + created issue."""
    issue_id = event.get("issue_id") or ""
    fingerprint = event.get("fingerprint") or event.get("culprit", "")[:200]
    level = event.get("level", "error")
    return {
        "type": "incident",
        "repo": repo,
        "sha": "",  # Sentry lacks SHA; use empty per dedup rules
        "pr_number": None,
        "source": "observability",
        "severity": level,
        "fingerprint": fingerprint or issue_id,
        "title": build_sentry_issue_title(event),
        "summary": f"Sentry issue #{issue_number}",
        "paths": [],
        "links": [{"url": f"https://github.com/{repo}/issues/{issue_number}", "type": "github_issue"}],
        "metadata": {"issue_id": issue_id, "sentry_event": event.get("id")},
    }
```

### Config Propagation
**What:** get_memory_config(booty_config) requires booty_config with `.memory` attribute. When memory block absent, returns None → skip add_record.

**When:** Every call site. If config is None, skip the add_record call (or pass and let add_record handle via config.enabled — but get_memory_config returns None when block missing, so we'd need to handle).

**Pattern:**
```python
mem_config = get_memory_config(booty_config) if booty_config else None
if mem_config and mem_config.enabled:
    record = build_incident_record(...)
    add_record(record, mem_config)
```

### Fire-and-Forget with Logging
**What:** Wrap add_record in try/except; log on failure. Ingestion must not block agent success.

**When:** All call sites.

```python
try:
    if mem_config and mem_config.enabled:
        result = add_record(record, mem_config)
        if result.get("added"):
            logger.debug("memory_record_added", type=record["type"], id=result.get("id"))
except Exception as e:
    logger.warning("memory_ingestion_failed", type=record.get("type"), error=str(e))
```

### Record Types and Required Fields

| Type | Required Fields | Fingerprint | Notes |
|------|-----------------|-------------|-------|
| incident | type, repo, source, severity, title, timestamp | issue_id or culprit | SHA empty; dedup by (type, repo, fingerprint) |
| governor_hold | type, repo, sha, source, reason, title | decision.reason | pr_number from merge? Governor has head_sha only |
| deploy_failure | type, repo, sha, source, conclusion, run_url | sha | metadata.conclusion, metadata.failure_type |
| security_block | type, repo, sha, pr_number, source, title | per CONTEXT | metadata.trigger: secret/vulnerability/permission_drift |
| verifier_cluster | type, repo, sha, pr_number, source, failure_type | `<failure_type>:<paths_hash>` | One per class: import, compile, test |
| revert | type, repo, sha, source, reverted_sha | sha | metadata.reverted_sha |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Dedup logic | Custom per-source | add_record's built-in | MEM-14; 24h window; (type, repo, sha, fingerprint, pr_number) |
| State dir | Custom path | get_memory_state_dir() | Shared with Phase 22 |
| Record validation | Manual schema check | add_record + schema fields | Schema is flexible (total=False) |
| Revert git parsing | Complex regex | Simple: "Revert" in message, or "revert " + sha pattern | CONTEXT: git message or explicit input |

## Common Pitfalls

### Pitfall 1: Config Not Loaded at Call Site
**What goes wrong:** get_memory_config(None) or booty_config without memory block — either crashes or silently skips.
**Why it happens:** Webhooks load governor_config, not full booty_config; runners load booty_config for verifier/security, may not have memory.
**How to avoid:** Ensure each wiring point loads full BootyConfig from .booty.yml; pass to get_memory_config.
**Warning signs:** No records in memory.jsonl despite events firing.

### Pitfall 2: Ingestion Blocks Agent Flow
**What goes wrong:** add_record raises, agent fails to post status/create issue.
**Why it happens:** Network/disk errors in append_record.
**How to avoid:** try/except around add_record; log and continue.
**Warning signs:** Observability stops creating issues when memory has a bug.

### Pitfall 3: Verifier One Record Per Failure Class
**What goes wrong:** Single verifier_cluster for "import + compile" — lookup can't distinguish.
**Why it happens:** CONTEXT says one per class; combined failures = multiple records.
**How to avoid:** On import failure: add_record(import). On compile failure: add_record(compile). Both: two calls.
**Warning signs:** Single record when both import and compile fail.

### Pitfall 4: Security ESCALATE vs FAIL Same Type
**What goes wrong:** Both are security_block; lookup can't tell permission_drift from secret.
**Why it happens:** MEM-09 and MEM-10 both store security_block.
**How to avoid:** metadata.trigger: "secret" | "vulnerability" | "permission_drift". fingerprint/reason distinguishes.
**Warning signs:** Surfacing shows "blocking" for ESCALATE (permission_drift is informational).

### Pitfall 5: Spooled Observability Events
**What goes wrong:** create_sentry_issue_with_retry returns None (spooled); we never ingest.
**Why it happens:** CONTEXT says "ingest on successful issue creation". Spooled = deferred.
**How to avoid:** Ingest only when issue_number is not None. Spooled events ingested when/if retry succeeds (separate process or manual) — may be out of scope for Phase 23.
**Warning signs:** Incidents from retried spool missing from memory.

## Code Examples

### Observability Adapter Call (webhooks.py)
```python
# After: if issue_number is not None
from booty.memory import add_record, get_memory_config
from booty.memory.adapters import build_incident_record

booty_config = _load_booty_config_for_repo(settings.TARGET_REPO_URL)  # New helper
mem_config = get_memory_config(booty_config) if booty_config else None
if mem_config and mem_config.enabled:
    try:
        record = build_incident_record(event, issue_number, repo_from_url(settings.TARGET_REPO_URL))
        add_record(record, mem_config)
    except Exception as e:
        logger.warning("memory_ingestion_failed", type="incident", error=str(e))
```

### Governor HOLD Adapter Call (webhooks.py)
```python
# In branch: else (decision.outcome != "ALLOW"), after post_hold_status
if mem_config and mem_config.enabled:
    try:
        record = build_governor_hold_record(decision, repo_full_name)
        add_record(record, mem_config)
    except Exception as e:
        logger.warning("memory_ingestion_failed", type="governor_hold", error=str(e))
```

### Deploy Failure (webhooks.py)
```python
# In is_deploy branch, when conclusion in ("failure", "cancelled"), after create_or_append_deploy_failure_issue
record = build_deploy_failure_record(head_sha, run_url, conclusion, failure_type, repo_full_name)
# ... add_record
```

### Security FAIL (runner.py)
```python
# At each edit_check_run(conclusion="failure") — secret, vuln, audit error, generic
trigger = "secret" | "vulnerability" | "permission_drift"  # from context
record = build_security_block_record(job, trigger, title, summary, paths)
add_record(record, mem_config)
```

### Verifier FAIL (runner.py)
```python
# Per failure class: import, compile, test
# Fingerprint: f"{failure_type}:{hash_of_paths}"
for failure_class in ["import", "compile", "test"]:  # only those that failed
    record = build_verifier_cluster_record(job, failure_class, ...)
    add_record(record, mem_config)
```

## State of the Art

| Approach | Current | Impact |
|----------|---------|--------|
| Inline record construction | Adapter functions in memory/adapters.py | Reusable, testable, single schema source |
| Config in every agent | Central load in webhooks; runners use existing config load | No duplicate .booty.yml fetches |
| Synchronous add_record | Same request/response | Simple; add_record is fast (append + dedup scan) |

## Open Questions

1. **Revert detection on push to main**
   - What we know: CONTEXT says git message "Revert ..." or "revert <sha>"; GitHub revert merge metadata; main only.
   - What's unclear: Does Booty receive `push` events? Webhooks show pull_request, workflow_run, issues. Need push handler.
   - Recommendation: Add `push` event handling for ref=main; parse commit message; or defer revert to Phase 23 Plan (CLI + Builder explicit input first; push detection if webhook supports it).

2. **paths_hash for verifier fingerprint**
   - CONTEXT: fingerprint = `<failure_type>:<paths_hash>`. Exact algorithm left to Claude.
   - Recommendation: Use hashlib.sha256("|".join(sorted(paths)).encode()).hexdigest()[:16].

3. **Governor HOLD pr_number**
   - Governor has head_sha from verification workflow_run. PR that produced that SHA requires API lookup (commit.get_pulls()).
   - Recommendation: pr_number can be None for governor_hold; dedup still works with (type, repo, sha, fingerprint).

## Sources

### Primary (HIGH confidence)
- Phase 22 implementation: src/booty/memory/api.py, config.py, schema.py
- Phase 23 CONTEXT.md — record types, fingerprint rules, deferrals
- webhooks.py — sentry, workflow_run flows
- security/runner.py — FAIL/ESCALATE paths
- verifier/runner.py — import, compile, test, install failure paths
- release_governor/failure_issues.py, handler.py

### Secondary (MEDIUM confidence)
- REQUIREMENTS.md MEM-06 to MEM-12
- GitHub webhook events (push vs workflow_run)

### Tertiary (LOW confidence)
- Sentry event structure for fingerprint — verify payload shape in production

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all in codebase
- Architecture: HIGH — adapter pattern matches existing Booty style
- Pitfalls: HIGH — from CONTEXT and code inspection

**Research date:** 2026-02-16
**Valid until:** 30 days (stable integration)
