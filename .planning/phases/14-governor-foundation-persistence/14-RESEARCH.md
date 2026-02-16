# Phase 14: Governor Foundation & Persistence - Research

**Researched:** 2026-02-16
**Domain:** Config schema extension, file-based state store, GitHub Actions workflow inputs, Verifier reuse
**Confidence:** HIGH

## Summary

Phase 14 delivers the Release Governor foundation: config schema in .booty.yml with env overrides, file-based release state with atomic writes, delivery ID cache for idempotency, agent module skeleton, deploy workflow sha input, and verify-main workflow. The codebase already uses BootyConfigV1 with `extra="forbid"`, Pydantic Settings, and YAML loading. Standard approach: extend BootyConfigV1 with optional `release_governor` block; use write-then-replace (temp file + os.replace) for atomic JSON writes; use fcntl.flock for single-writer coordination; reuse Verifier logic for verify-main workflow.

**Primary recommendation:** Extend BootyConfigV1 with ReleaseGovernorConfig; use stdlib (os.replace, fcntl, tempfile, json) for state store; add workflow inputs for sha to deploy.yml; create verify-main.yml that runs Verifier logic on push to main.

## Standard Stack

### Core
| Library | Purpose | Why Standard |
|---------|---------|--------------|
| Pydantic v2 | Config validation | Already in project; ConfigDict(extra="forbid") for strict schema |
| pydantic-settings | Env overrides | Already in project; env_prefix for RELEASE_GOVERNOR_* |
| PyYAML | .booty.yml parsing | Already used for config loading |
| Python stdlib (fcntl, tempfile, json, os) | Atomic file writes | No new deps; write temp + os.replace is atomic on POSIX |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| pathlib.Path | State directory | Consistent with existing config.py usage |
| structlog | Logging | Project standard |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib fcntl + os.replace | filelock, portalocker | stdlib sufficient for single-writer; no new deps |
| Separate delivery_ids.json | Combined release.json | CONTEXT says separate files; follow decision |

## Architecture Patterns

### Recommended Project Structure
```
src/booty/
├── release_governor/
│   ├── __init__.py      # Exports, is_enabled check
│   ├── config.py        # ReleaseGovernorConfig model, load from booty config
│   ├── store.py         # ReleaseState, DeliveryCache, atomic write, flock
│   └── handler.py       # Placeholder stubs (no-op until Phase 15)
├── test_runner/config.py  # Extend BootyConfigV1 with release_governor
```

### Pattern 1: Atomic JSON File Write
**What:** Write to temp file in same directory, fsync, close, then os.replace.
**When to use:** Any persistent state that must survive crashes mid-write.
**Example:**
```python
# Write atomically: temp in same dir, then rename
with tempfile.NamedTemporaryFile(mode='w', dir=state_dir, delete=False, suffix='.tmp') as f:
    json.dump(data, f, indent=2)
    f.flush()
    os.fsync(f.fileno())
temp_path = f.name
os.replace(temp_path, target_path)
```

### Pattern 2: fcntl.flock for Single-Writer
**What:** Acquire exclusive lock before read/write; release on close.
**When to use:** Cross-process coordination; single writer, multiple readers OK with shared lock for reads.
**Example:**
```python
import fcntl
with open(path, 'r+') as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    try:
        data = json.load(f)
        # ... modify ...
        f.seek(0)
        f.truncate()
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    finally:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**Note:** For atomic replace pattern, write to temp (no shared state), then os.replace. flock on the target before replace if you need to block readers during swap. CONTEXT allows "lock scope (per-file vs per-operation)" as Claude's discretion — per-file (lock around whole read-modify-write) is simplest.

### Anti-Patterns to Avoid
- **Don't write directly to target file:** Partial writes on crash corrupt state. Always temp + replace.
- **Don't add filelock dependency:** stdlib fcntl suffices for single-writer; project avoids new deps where possible.
- **Don't hand-roll YAML parsing:** Use existing load_booty_config_from_content and extend schema.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Config validation | Custom validation | Pydantic model_validate + extra="forbid" | Schema drift, unknown keys already handled |
| Env overrides | Manual os.environ | pydantic-settings or manual RELEASE_GOVERNOR_* mapping | Consistent with existing Settings pattern |
| Atomic write | In-place file edit | tempfile + os.replace | Guarantees all-or-nothing |
| JSON serialization | Custom parser | json module | Stdlib, well-tested |

## Common Pitfalls

### Pitfall 1: os.replace on Windows
**What goes wrong:** On Windows, os.replace may fail if target is open.
**Why it happens:** Windows file locking differs from POSIX.
**How to avoid:** Close temp file before os.replace; Booty runs on Linux (deploy targets, Actions). If Windows support needed later, add filelock.
**Warning signs:** CI on windows-latest failing on state write.

### Pitfall 2: Delivery ID cache unbounded growth
**What goes wrong:** delivery_ids.json grows forever.
**Why it happens:** No pruning of old (repo, sha) entries.
**How to avoid:** CONTEXT defers exact structure to Claude's discretion. Recommend: keep last N entries per repo or TTL-based eviction; Phase 14 can ship with simple append-only and defer pruning to later if needed.
**Warning signs:** File size growing without bound.

### Pitfall 3: deploy workflow sha not passed to remote
**What goes wrong:** Workflow checks out sha locally, but deploy.sh SSHs and runs `git pull` on remote — deploys latest main, not requested sha.
**Why it happens:** deploy.sh doesn't accept sha; it always pulls DEPLOY_BRANCH.
**How to avoid:** Pass DEPLOY_SHA from workflow to deploy.sh; when set, remote does `git fetch origin && git checkout $DEPLOY_SHA` instead of checkout + pull.
**Warning signs:** Manual workflow_dispatch with sha deploys wrong commit.

### Pitfall 4: verify-main duplicates Verifier code
**What goes wrong:** Copy-paste of runner logic; maintenance burden.
**Why it happens:** Workflow runs in different context (push vs pull_request).
**How to avoid:** Extract reusable function (e.g. run_verification(workspace_path, head_sha, config)) from Verifier; verify-main job invokes it. Or: verify-main workflow triggers a "verification job" that uses same code path.
**Warning signs:** Two copies of test execution logic.

## Code Examples

### BootyConfigV1 Extension
```python
# In test_runner/config.py - add optional nested model
class ReleaseGovernorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    production_environment_name: str = "production"
    require_approval_for_first_deploy: bool = False
    high_risk_paths: list[str] = Field(default_factory=lambda: [".github/workflows/**", "**/migrations/**"])
    deploy_workflow_name: str = "deploy.yml"
    deploy_workflow_ref: str = "main"
    cooldown_minutes: int = 30
    max_deploys_per_hour: int = 6
    approval_mode: Literal["environment", "label", "comment"] = "environment"

class BootyConfigV1(BaseModel):
    # ... existing fields ...
    release_governor: ReleaseGovernorConfig | None = None
```

### GitHub Actions workflow_dispatch with inputs
```yaml
on:
  workflow_dispatch:
    inputs:
      sha:
        description: 'SHA to deploy (required for governor-triggered deploys)'
        required: false
        type: string
jobs:
  deploy:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.sha || github.sha }}
          fetch-depth: 0
```

### deploy.sh SHA support
```bash
# When DEPLOY_SHA is set, checkout that SHA instead of branch
if [ -n "$DEPLOY_SHA" ]; then
  git fetch origin
  git checkout "$DEPLOY_SHA"
else
  git checkout "$DEPLOY_BRANCH"
  git pull origin "$DEPLOY_BRANCH"
fi
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| In-place file write | Temp + os.replace | Crash-safe; partial writes never persist |
| Polling for deploy | workflow_dispatch with sha | Governor triggers exact SHA; no race |
| Hardcoded deploy trigger | workflow_dispatch-only (Phase 15) | Governor gates all production deploys |

**Deprecated/outdated:** None relevant for this phase.

## Open Questions

1. **State directory path**
   - What we know: CONTEXT says "app/data directory (e.g. $HOME/.booty/state/ or configurable path), not inside the repo"
   - What's unclear: Exact default; project may use /opt/booty or similar on server
   - Recommendation: Default to `$HOME/.booty/state/` when HOME set, else `./.booty/state/`; make path configurable via env RELEASE_GOVERNOR_STATE_DIR

2. **verify-main: reuse vs new workflow**
   - What we know: Should mirror Verifier logic; Verifier runs in GitHub Actions (repository_dispatch or pull_request)
   - What's unclear: Whether verify-main is a separate workflow that runs tests, or triggers the app's verifier
   - Recommendation: New workflow verify-main.yml that runs on push to main; checkout main; runs same test/lint steps as Verifier (setup_command, install_command, test_command from .booty.yml). Reuse by extracting shell steps or calling booty CLI if available.

## Sources

### Primary (HIGH confidence)
- Existing codebase: src/booty/test_runner/config.py, .github/workflows/deploy.yml
- Python docs: fcntl, tempfile, os.replace
- CONTEXT.md phase decisions

### Secondary (MEDIUM confidence)
- WebSearch: atomic file write patterns, flock vs lockf

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all components already in project or stdlib
- Architecture: HIGH - patterns match existing Booty structure
- Pitfalls: MEDIUM - deploy.sh sha wiring confirmed; verify-main reuse needs implementation check

**Research date:** 2026-02-16
**Valid until:** 30 days
