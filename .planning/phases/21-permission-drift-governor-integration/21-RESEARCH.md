# Phase 21: Permission Drift & Governor Integration - Research

**Researched:** 2026-02-16
**Domain:** Path matching (sensitive paths), state persistence, Governor risk override integration
**Confidence:** HIGH

## Summary

Phase 21 connects Security's permission-drift detection with the Release Governor. When Security detects changes in sensitive paths (workflows, infra, terraform, helm, k8s, iam, auth, security), it ESCALATEs (does not FAIL), persists a risk override to shared state, and the Governor consumes that override before computing deploy decisions. The PR is not blocked — only deploy risk is escalated.

The codebase already provides all required primitives: PathSpec with gitwildmatch (risk.py, limits.py), SecurityConfig.sensitive_paths, Governor's compute_risk_class and get_state_dir, and the Security runner flow. No new libraries needed. Implementation is wiring and a new persistence layer.

**Primary recommendation:** Use PathSpec.from_lines("gitwildmatch", sensitive_paths) for matching; persist overrides to security_overrides.json in Governor's state dir; Governor reads override for each commit in diff before compute_risk_class; use risk_class=HIGH when override present.

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pathspec | 1.0.4 | Path pattern matching | Already used in risk.py, limits.py, code_gen/security; gitwildmatch semantics |
| PyGithub | (existing) | Compare API for diff | Governor uses repo.compare(); Security can use workspace git or PyGithub |
| json + pathlib | stdlib | Override persistence | Same pattern as store.py (release.json, delivery_ids.json) |

### Supporting

| Component | Purpose | When to Use |
|-----------|---------|-------------|
| git.Repo (GitPython) | git diff --name-status | Security has workspace with repo; get changed files base..head |
| fcntl + atomic write | Safe concurrent access | Same pattern as store.py for security_overrides.json |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PathSpec gitwildmatch | fnmatch, glob | PathSpec handles ** recursion, gitignore semantics; project standard |
| JSON file | SQLite, Redis | JSON matches store.py; single-writer from Security, read-only from Governor; no new deps |
| Poll for override | Event bus | Governor is sync webhook; poll is simpler, 2 min cap acceptable |

## Architecture Patterns

### Recommended Project Structure

```
src/booty/
├── security/
│   ├── permission_drift.py   # check_sensitive_paths_touched, get_changed_files
│   └── override.py           # persist_override, load_override (or in store)
├── release_governor/
│   ├── risk.py               # Add get_security_override_or_compute_risk
│   ├── store.py              # Or add security_overrides.json helpers
│   └── handler.py            # Call override check before compute_risk_class
```

### Pattern 1: Sensitive Path Matching

**What:** Match changed files against PathSpec from SecurityConfig.sensitive_paths.
**When to use:** After getting changed files from git diff.
**Example:**

```python
from pathspec import PathSpec

spec = PathSpec.from_lines("gitwildmatch", config.sensitive_paths)
for path in changed_paths:
    if spec.match_file(path):
        return True  # sensitive path touched
return False
```

**Renames:** Git diff --name-status returns `R100 old_path new_path`. Check both old_path and new_path against spec.

### Pattern 2: Override Persistence (mirror store.py)

**What:** JSON file with (repo, sha) keys; atomic write; LOCK_EX for write, LOCK_SH for read.
**When to use:** Security writes after ESCALATE; Governor reads before compute_decision.
**Example (structure):**

```json
{
  "owner/repo:abc123": {
    "risk_override": "HIGH",
    "reason": "permission_surface_change",
    "sha": "abc123",
    "paths": [".github/workflows/deploy.yml"],
    "created_at": "2026-02-16T12:00:00Z"
  }
}
```

### Pattern 3: Governor Override Integration

**What:** Before compute_risk_class, check each commit in the diff for override. If any has override, use risk_class=HIGH.
**When to use:** In handle_workflow_run and simulate_decision_for_cli.
**Flow:**

1. Get comparison (base..head) — already have this
2. For each file in comparison.files, get the commit(s) that changed it (or use head_sha for workflow_run — single commit)
3. For workflow_run: head_sha is the deploy candidate; check override for head_sha
4. For PR commits: CONTEXT says "persist for every commit in the PR; Governor checks each commit in the diff" — workflow_run has single head_sha; the "diff" in Governor is production_sha..head_sha (deploy diff). So we check head_sha, and if merge commit, we may need to check commits in the merge. Simplest: check head_sha. If override exists -> HIGH.
5. Poll up to 2 min if override not present (race: Governor runs before Security).

### Anti-Patterns to Avoid

- **Hand-rolling path matching:** Use PathSpec; don't use fnmatch or regex.
- **Blocking PR on ESCALATE:** ESCALATE = conclusion success, merge allowed; only deploy risk goes to HIGH.
- **Separate state dir for Security:** Use same get_state_dir() so Governor finds overrides.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|--------|-------------|--------------|-----|
| Path pattern matching | Custom glob/regex | PathSpec | ** support, gitignore semantics, project standard |
| Atomic JSON write | Ad-hoc file write | _atomic_write_json pattern from store.py | Prevents corruption |
| Concurrent read/write | Manual locking | fcntl LOCK_SH/LOCK_EX | Same as store.py |

## Common Pitfalls

### Pitfall 1: Rename detection

**What goes wrong:** Only checking new path on renames; old path was sensitive, escalation missed.
**Why it happens:** Git diff shows R100 old new; if only checking new, moving sensitive file to non-sensitive dir would miss.
**How to avoid:** Parse --name-status; for R, check both old and new paths.
**Warning signs:** Tests only cover add/modify, not rename.

### Pitfall 2: Override key collision

**What goes wrong:** Key format (repo:sha) ambiguous for forks or nested repos.
**Why it happens:** Full repo name can have slashes.
**How to avoid:** Use repo full_name (owner/repo) from payload; sha is 40-char. Key: f"{repo_full_name}:{sha}".
**Warning signs:** Key format differs from delivery_ids.json (which uses repo:sha).

### Pitfall 3: Race — Governor before Security

**What goes wrong:** Workflow_run fires before Security has finished and written override.
**Why it happens:** Security runs on pull_request; deploy workflow_run can trigger when PR merges; timing varies.
**How to avoid:** Governor polls for override up to 2 min (e.g. 5s intervals, 24 attempts); then proceeds without override.
**Warning signs:** Tests don't cover "override appears after first read".

### Pitfall 4: Unbounded override growth

**What goes wrong:** security_overrides.json grows forever.
**Why it happens:** Every PR writes overrides; no cleanup.
**How to avoid:** TTL 14 days; Governor prunes on read (remove expired entries when loading); optional: Security prunes on write.
**Warning signs:** No timestamp in override entries; no prune logic.

## Code Examples

### Get changed files from workspace (Security)

```python
def get_changed_paths(repo: git.Repo, base_sha: str, head_sha: str) -> list[tuple[str, str | None]]:
    """Return (path, old_path_or_none) for add/modify/delete/rename."""
    out = repo.git.diff("--name-status", "-z", base_sha, head_sha)
    # Parse NUL-separated: STATUS\tPATH[\tRENAME_TARGET]
    # A=add, M=modify, D=delete, R=rename
    result = []
    parts = out.split("\x00")
    i = 0
    while i < len(parts):
        if not parts[i]:
            i += 1
            continue
        status_and_path = parts[i]
        tab = status_and_path.find("\t")
        status = status_and_path[:1] if tab >= 0 else ""
        path = status_and_path[tab + 1:] if tab >= 0 else ""
        old_path = None
        if status == "R" and i + 1 < len(parts):
            old_path = path
            path = parts[i + 1]
            i += 1
        result.append((path, old_path))
        i += 1
    return result
```

### Match sensitive paths (both for renames)

```python
def sensitive_paths_touched(paths: list[tuple[str, str | None]], spec: PathSpec) -> list[str]:
    touched = []
    for path, old_path in paths:
        if spec.match_file(path):
            touched.append(path)
        elif old_path and spec.match_file(old_path):
            touched.append(old_path)
    return touched
```

## State of the Art

| Old Approach | Current Approach | Impact |
|-------------|------------------|--------|
| Custom path matching | PathSpec gitwildmatch | Consistent with risk.py, limits.py |
| In-memory only | JSON file in state dir | Persists across processes; Governor finds it |

**Deprecated/outdated:** None — project patterns are current.

## Open Questions

1. **Squash merge limitation:** CONTEXT documents that squash merge produces one new commit; PR commits not in diff. Override keyed by head_sha may not match. Governor's path-based risk may still catch if paths overlap. Recommendation: Document; accept limitation.
2. **Poll interval:** 5s × 24 = 2 min. Could use exponential backoff (2s, 4s, 8s...) to reduce load. Recommendation: Simple 5s fixed is fine.
3. **Category-to-title mapping:** CONTEXT leaves to Claude's discretion. Recommendation: Map path prefix to category — `.github/workflows/` → "workflow modified", `infra/` → "infra modified", etc. Default "Security escalated — permission surface changed" if no specific match.

## Sources

### Primary (HIGH confidence)
- src/booty/release_governor/risk.py — PathSpec usage, compute_risk_class
- src/booty/release_governor/store.py — get_state_dir, atomic write, delivery_ids pattern
- src/booty/release_governor/handler.py — handle_workflow_run, compute_risk_class call site
- src/booty/security/runner.py — process_security_job flow, workspace, config loading
- src/booty/test_runner/config.py — SecurityConfig.sensitive_paths

### Secondary (MEDIUM confidence)
- 21-CONTEXT.md — Implementation decisions, override key structure, lifecycle

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All components already in project
- Architecture: HIGH — Mirror existing patterns (risk.py, store.py)
- Pitfalls: HIGH — Derived from CONTEXT and codebase analysis

**Research date:** 2026-02-16
**Valid until:** ~30 days (stable domain)
