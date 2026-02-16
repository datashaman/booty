# Phase 27: Planner Foundation - Research

**Researched:** 2026-02-16
**Domain:** Booty internal — plan schema, config, webhook routing, CLI patterns
**Confidence:** HIGH

## Summary

Phase 27 adds Planner Agent foundation: Pydantic plan schema, optional .booty.yml planner block, GitHub webhook handling for `agent:plan`, and `booty plan` CLI. All patterns exist in the codebase — Memory (Phase 22), Security (Phase 18), Governor, webhooks, and CLI provide direct templates. No new external dependencies. Key: follow established patterns for config blocks (raw dict + lazy validation), state dirs (env override → $HOME/.booty/state), webhook branching (separate early returns), and CLI groups (click.group).

**Primary recommendation:** Mirror Memory and Security patterns for config; mirror webhook check_run/pull_request branching for agent:plan; mirror memory/governor CLI for booty plan.

## Standard Stack

### Core (existing)
| Component | Purpose | Source |
|-----------|---------|--------|
| Pydantic | Plan schema, config validation | test_runner/config.py, memory/config.py |
| Click | CLI | cli.py |
| FastAPI | Webhook routes | webhooks.py |

### Config Block Pattern
| Pattern | Example | Use |
|---------|---------|-----|
| BootyConfigV1 optional block | memory: dict \| None, security: SecurityConfig \| None | Add planner: dict \| None |
| field_validator(mode="before") | validate_memory_block, validate_security_block | Lazy validation or strict |
| apply_*_env_overrides | apply_memory_env_overrides | PLANNER_* env overrides |

### State Dir Pattern
| Function | Env Var | Fallback |
|----------|---------|----------|
| get_memory_state_dir | MEMORY_STATE_DIR | $HOME/.booty/state, ./.booty/state |
| get_state_dir (Governor) | RELEASE_GOVERNOR_STATE_DIR | same |
| get_planner_state_dir | PLANNER_STATE_DIR | same |

## Architecture Patterns

### Webhook Event Branching
```python
# webhooks.py pattern: early return by event_type
if event_type == "check_run":
    # handle check_run, return
if event_type == "pull_request":
    # handle pull_request, return
# issues: labeled (builder)
```

Add before Builder issues block:
```python
if event_type == "issues":
    action = payload.get("action")
    if action in ("opened", "labeled"):
        labels = [l.get("name") for l in payload.get("issue", {}).get("labels", [])]
        if "agent:plan" in labels:
            # Enqueue PlannerJob, return 202
```

### Config Block (Memory/Security style)
```python
# memory: raw dict, lazy validation
memory: dict | None = None
@field_validator("memory", mode="before")
def validate_memory_block(cls, v): ...

# security: strict, invalid -> None
security: SecurityConfig | None = None
@field_validator("security", mode="before")
def validate_security_block(cls, v):
    try: return SecurityConfig.model_validate(v)
    except ValidationError: return None
```

Planner: use Security style (PlannerConfig with extra="forbid") — env overrides only, minimal fields.

### Plan Storage Paths
- Issue: `plans/<owner>/<repo>/<issue_number>.json` (nested, multi-repo)
- Ad-hoc: `plans/ad-hoc-<timestamp>-<short_hash>.json`
- Base: get_planner_state_dir() / "plans"

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| State dir resolution | Custom path logic | get_planner_state_dir() mirroring get_memory_state_dir |
| JSON atomic write | Manual fsync | release_governor/store._atomic_write_json pattern |
| Webhook HMAC | Custom crypto | verify_signature (existing) |
| CLI structure | New framework | Click groups (memory, governor) |

## Common Pitfalls

### Webhook Action Handling
**Pitfall:** Only checking `action == "labeled"` misses issues opened with agent:plan already applied.
**Fix:** Accept both `opened` and `labeled`; for `labeled` verify label name is agent:plan; for `opened` check labels include agent:plan.

### Job Type Mixing
**Pitfall:** Reusing Builder Job for Planner causes process_job to run Builder logic.
**Fix:** Introduce PlannerJob dataclass; separate planner_queue and planner_worker; route by job type.

### Ad-hoc Collision
**Pitfall:** Two ad-hoc plans in same second get same path.
**Fix:** Include short hash of content (e.g. first 8 chars of hashlib.sha256(text.encode()).hexdigest()).

## Code Examples

### get_memory_state_dir (store.py)
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

### BootyConfigV1 security block (test_runner/config.py)
```python
security: SecurityConfig | None = Field(default=None, ...)
@field_validator("security", mode="before")
def validate_security_block(cls, v):
    if v is None: return None
    if isinstance(v, dict):
        try: return SecurityConfig.model_validate(v)
        except ValidationError: return None
    return None
```

### Webhook early return (webhooks.py ~195)
```python
if event_type == "check_run":
    # ... handle, return
if event_type == "pull_request":
    # ... handle, return
# Later: action != "labeled" -> ignore (for Builder)
```

## Open Questions

1. **Planner worker concurrency:** Single worker or pool? Recommend 1 for Phase 27 (plan gen is Phase 29; stub is cheap).
2. **PlannerJob vs extending Job:** New dataclass clearer than polymorphic Job — PlannerJob(issue_number, repo_url, payload, ...).

## Sources

### Primary (HIGH confidence)
- src/booty/webhooks.py — webhook branching, HMAC, enqueue
- src/booty/test_runner/config.py — BootyConfigV1, SecurityConfig, Memory block
- src/booty/memory/store.py — get_memory_state_dir
- src/booty/memory/config.py — MemoryConfig, apply_memory_env_overrides
- src/booty/cli.py — Click groups (memory, governor)
- src/booty/jobs.py — Job, JobQueue

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all internal, patterns verified in codebase
- Architecture: HIGH — direct copy from Memory/Security/Governor
- Pitfalls: MEDIUM — based on similar phases (13, 18, 22)

**Research date:** 2026-02-16
**Valid until:** 30 days
