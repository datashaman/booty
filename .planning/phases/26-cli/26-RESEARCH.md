# Phase 26: CLI — Research

**Researched:** 2026-02-16
**Domain:** Booty CLI extension (click, memory module)
**Confidence:** HIGH

## Summary

Phase 26 adds two Memory CLI subcommands: `booty memory status` and `booty memory query`. The work is internal extension of the existing click-based CLI (`src/booty/cli.py`). No new external dependencies. Patterns exist in `booty governor status|simulate|trigger` and `booty memory ingest revert`.

Key implementation points:
- **status**: Load config via `load_booty_config(workspace)`; use `get_memory_config` + `apply_memory_env_overrides`; read `memory.jsonl` via `store.read_records` for record count; filter by retention for count-in-retention (optional, per MEM-27 "record count").
- **query**: Mutually exclusive `--pr <n>` or `--sha <sha>`; both resolve to (paths, repo). For `--pr`: `gh_repo.get_pull(n).get_files()` → paths. For `--sha`: `_find_pr_for_commit` (surfacing) or `commit.get_pulls()` → PR → paths. Call `memory.query(paths, repo, config=mem_config)`; output human-readable or `--json` per MEM-28.
- Config loading follows `booty memory ingest revert`: workspace/repo, `load_booty_config` or `.booty.yml` from repo; require `--repo` when cannot infer from git.

**Primary recommendation:** Extend `booty memory` group with `status` and `query` subcommands; reuse governor/ingest patterns; GITHUB_TOKEN required for query (PR/sha resolution).

## Standard Stack

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| click | (existing) | CLI framework | Already in use for booty |
| PyGithub | (existing) | GitHub API for PR files, commit.get_pulls | Already used by surfacing, webhooks |
| booty.memory | (Phase 22–24) | query, store, config | In-project; no new deps |

**No new dependencies.** Use existing booty.memory and click.

## Architecture Patterns

### Existing CLI Patterns (from cli.py)

- **Group nesting:** `cli` → `governor` → `status|simulate|trigger`; `cli` → `memory` → `ingest` → `revert`.
- **Workspace/repo:** `--workspace` defaults to `.`; repo from `--repo` or `_infer_repo_from_git(workspace)`.
- **JSON output:** `--json` / `as_json` flag; `json.dumps(out)` for machine-readable.
- **Config loading:** `load_booty_config(ws)`; handle missing config (echo disabled, exit 0 or 1 per command semantics).
- **Memory enabled check:** `get_memory_config(config)` + `apply_memory_env_overrides`; if `not mem_config or not mem_config.enabled` → "Memory disabled".

### PR Path Resolution

- `pr.get_files()` → list of File objects with `.filename` (webhooks.py:224).
- `paths = [f.filename for f in pr.get_files()]`
- For `--sha`: `commit = gh_repo.get_commit(sha)`; `pulls = commit.get_pulls()`; first PR number → `repo.get_pull(n)` → `get_files()` → paths. Matches `surfacing._find_pr_for_commit` pattern.

### Query Output Format

- Human: Per match line like `- **{type}** ({date}) — {summary} [link]` (matches `format_matches_for_pr` / `format_matches_for_incident`).
- JSON: List of `{type, timestamp, summary, links, id}` (lookup.result_subset shape).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|--------|-------------|--------------|-----|
| PR file list | Manual diff/compare | `pr.get_files()` | PyGithub provides this; webhooks use it |
| Record count | Custom line counting | `read_records(path)` then len + retention filter | store.read_records handles partial lines |
| Repo inference | Custom git parsing | `_infer_repo_from_git(ws)` | Already in cli.py |

## Common Pitfalls

### Pitfall 1: Missing GITHUB_TOKEN for query
**What goes wrong:** `--pr` / `--sha` require GitHub API; missing token fails.
**How to avoid:** Check token early; echo "GITHUB_TOKEN required" and exit 1 (like governor simulate, ingest revert).

### Pitfall 2: --pr and --sha both provided
**What goes wrong:** Ambiguous which to use.
**How to avoid:** Mutual exclusivity; raise `click.UsageError` if both given.

### Pitfall 3: Memory disabled but query attempted
**What goes wrong:** Query with disabled config is confusing.
**How to avoid:** For query, if memory disabled, echo "Memory disabled" and exit 0 (per ingest revert) or exit 1 with hint; document in help.

## Code Examples

### status output (per MEM-27)
```
enabled: true
records: 42
retention_days: 90
```

When disabled:
```
Memory disabled
```

### query --pr flow
```python
gh = Github(token)
repo = gh.get_repo(repo_name)
pr = repo.get_pull(pr_number)
paths = [f.filename for f in pr.get_files()]
matches = memory.query(paths=paths, repo=repo_name, config=mem_config, state_dir=state_dir)
```

### query --sha flow
```python
commit = gh_repo.get_commit(sha)
pulls = commit.get_pulls()
pr = next(iter(pulls), None)
if not pr:
    click.echo("No PR found for sha", err=True)
    raise SystemExit(1)
paths = [f.filename for f in pr.get_files()]
matches = memory.query(paths=paths, repo=repo_name, config=mem_config, state_dir=state_dir)
```

## Sources

### Primary (HIGH confidence)
- `src/booty/cli.py` — governor status/simulate/trigger, memory ingest revert
- `src/booty/memory/surfacing.py` — _find_pr_for_commit, format_matches_for_pr
- `src/booty/webhooks.py` — pr.get_files(), surface_pr_comment call
- `src/booty/memory/lookup.py` — query signature
- `src/booty/memory/store.py` — read_records, get_memory_state_dir

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing codebase patterns
- Architecture: HIGH — cli.py and memory module inspected
- Pitfalls: HIGH — known from similar commands

**Research date:** 2026-02-16
**Valid until:** 30 days (stable internal extension)
