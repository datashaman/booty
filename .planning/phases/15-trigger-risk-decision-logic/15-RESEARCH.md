# Phase 15: Trigger, Risk & Decision Logic - Research

**Researched:** 2026-02-16
**Domain:** GitHub workflow_run webhooks, PyGithub compare API, risk scoring, pathspec matching
**Confidence:** HIGH

## Summary

Phase 15 implements the Governor's trigger (workflow_run), risk scoring (paths vs production_sha), decision rules (LOW/MEDIUM/HIGH + holds), and cooldown/rate limiting. The codebase already has PyGithub, pathspec, release state store, and config. Standard approach: add workflow_run branch to existing `/webhooks/github` route; use `repo.compare(base, head)` to get changed files; pathspec for HIGH/MEDIUM risk; extend ReleaseGovernorConfig with medium_risk_paths; extend store for deploy history (rate limit); pure decision function with hard holds and approval checks.

**Primary recommendation:** Use `repo.compare(production_sha, head_sha)` for diff; pathspec for path matching; extend config with medium_risk_paths; extend release.json with deploy_history for rate limit; add verification_workflow_name to config for workflow_run filtering.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyGithub | (existing) | repo.compare(base, head) for diff | Already in project; comparison.files gives changed paths |
| pathspec | (existing) | Path pattern matching | Already used in verifier limits, code_gen security |
| Pydantic | v2 | Decision/risk models | Project standard |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| structlog | Logging | Project standard |
| Python stdlib | datetime, json | Cooldown/rate limit calculations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| repo.compare() | GitHub API direct | PyGithub abstracts, already in project |
| pathspec | fnmatch/glob | pathspec handles ** recursion, gitignore semantics |

## Architecture Patterns

### Recommended Project Structure
```
src/booty/release_governor/
├── __init__.py
├── config.py        # (Phase 14) + medium_risk_paths, verification_workflow_name
├── store.py         # (Phase 14) + deploy_history for rate limit
├── risk.py          # compute_risk_class(comparison, config)
├── decision.py      # compute_decision(risk, state, config, approval_context)
└── handler.py       # handle_workflow_run(payload) - full pipeline
```

### Pattern 1: PyGithub Compare for Changed Files
**What:** Compare two commits to get list of changed file paths for risk scoring.
**When to use:** Need diff between production_sha and head_sha.
**Example:**
```python
# Source: Context7 PyGithub
repo = g.get_repo("owner/repo")
comparison = repo.compare(production_sha, head_sha)
for file in comparison.files:
    path = file.filename  # e.g. "src/app.py"
    # match against pathspecs
```

### Pattern 2: Pathspec for Risk Classification
**What:** Match file paths against configurable patterns (HIGH, MEDIUM).
**When to use:** Risk scoring per GOV-06, GOV-07.
**Example:**
```python
from pathspec import PathSpec
spec = PathSpec.from_lines('gitwildmatch', config.high_risk_paths)
if spec.match_file(path):
    return "HIGH"
```

### Pattern 3: workflow_run Payload Structure
**What:** GitHub sends workflow_run when a workflow completes.
**Relevant fields:**
- `action`: "completed"
- `workflow_run.conclusion`: "success" | "failure" | "cancelled" | ...
- `workflow_run.head_sha`: SHA that ran
- `workflow_run.name`: Workflow name (e.g. "Verify main")
- `repository.full_name`, `repository.owner.login`, `repository.name`

### Anti-Patterns to Avoid
- **Don't use GITHUB_SHA in workflow_run:** Use `workflow_run.head_sha` — GITHUB_SHA can be default branch (Phase 11 RESEARCH).
- **Don't skip conclusion check:** Only process `conclusion == "success"`.
- **Don't hand-roll path matching:** Use pathspec; project already uses it for limits.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Git diff between commits | subprocess git diff | PyGithub repo.compare() | No local clone; uses GitHub API |
| Path pattern matching | regex/fnmatch | pathspec | Gitignore semantics, ** support |
| Deploy history for rate limit | Custom format | JSON list in release.json | Consistent with existing store |

## Common Pitfalls

### Pitfall 1: repo.compare(base, head) Argument Order
**What goes wrong:** base/head reversed yields wrong diff direction.
**Why it happens:** compare(base, head) = "what changed from base to head". For risk we want "what's in head_sha that isn't in production_sha" = compare(production_sha, head_sha).
**How to avoid:** base=production_sha (old), head=head_sha (new). Compare gives files changed in head.
**Warning signs:** Empty diff when it shouldn't be; risk always LOW.

### Pitfall 2: Empty Diff Edge Case
**What goes wrong:** comparison can be empty (identical SHAs, bad refs).
**Why it happens:** production_sha == head_sha or invalid SHAs.
**How to avoid:** CONTEXT says "Empty diff: treat as LOW — allow". Return LOW, allow.
**Warning signs:** Crash on empty comparison.files.

### Pitfall 3: Approval Check Requires PR Lookup
**What goes wrong:** Label/comment approval needs the PR merged to produce head_sha. Finding that PR is non-trivial.
**Why it happens:** Commits can have multiple PRs; merge commits.
**How to avoid:** GitHub API: `repo.get_commit(sha).get_pulls()` or use Search API. PyGithub: `commit.get_pulls()` returns associated PRs. Check most recent merged PR.
**Warning signs:** Approval never found when it exists.

## Code Examples

### PyGithub Compare and Iterate Files
```python
# Source: Context7 PyGithub
comparison = repo.compare(production_sha, head_sha)
for file in comparison.files:
    print(f"{file.filename}: {file.status}")
```

### Pathspec Match (from limits.py)
```python
from pathspec import PathSpec
spec = PathSpec.from_lines('gitwildmatch', patterns)
if spec.match_file(relative_path):
    # matched
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Poll for workflow status | workflow_run webhook | Event-driven; GitHub pushes on completion |
| Git diff in workspace | GitHub Compare API | No clone; works from any environment |

## Open Questions

1. **verification_workflow_name config:** Add to ReleaseGovernorConfig to filter which workflow_run triggers Governor. Default "Verify main" to match verify-main.yml.
2. **deploy_history store shape:** Add `deploy_history: [{sha, time, result}]` to release.json, max 24 entries, evict older. Used for max_deploys_per_hour.
3. **Approval PR lookup:** Use `commit.get_pulls()` (PyGithub) — verify it returns merged PR for the commit.

## Sources

### Primary (HIGH confidence)
- Context7 PyGithub - compare, files iteration
- Phase 14 RESEARCH.md, 14-RESEARCH.md - config, store
- Phase 11 RESEARCH.md - workflow_run head_sha pitfall
- src/booty/verifier/limits.py - pathspec usage

### Secondary (MEDIUM confidence)
- Phase 15 CONTEXT.md - decisions on risk, approval, degraded

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PyGithub, pathspec in project; compare API verified
- Architecture: HIGH - aligns with Phase 14, webhook patterns
- Pitfalls: HIGH - Phase 11 docs head_sha; pathspec from limits.py

**Research date:** 2026-02-16
**Valid until:** ~30 days (stable APIs)
