# Phase 9: Diff Limits + .booty.yml Schema v1 - Research

**Researched:** 2026-02-15
**Domain:** GitHub PR diff stats, Pydantic schema strictness, Booty Verifier pipeline
**Confidence:** HIGH

## Summary

Phase 9 enforces diff limits and validates extended .booty.yml schema v1. The Verifier runs schema validation and limit checks **before** cloning when possible (agent PRs only). PyGithub provides PR diff stats directly (`pr.changed_files`, `pr.additions`, `pr.deletions`). Pydantic v2 supports `model_config = ConfigDict(extra='forbid')` for strict schema validation.

**Primary recommendation:** Extend BootyConfig with schema_version and new fields; add `load_booty_config_from_content()` for API-fetched YAML. Create `verifier/limits.py` with `get_pr_diff_stats()` and `check_diff_limits()`. Integrate into runner: fetch .booty.yml via `repo.get_contents()`, validate schema, check limits (agent PRs only), then proceed to clone + tests.

## Standard Stack

### Core (Use These)

| Library/Pattern | Purpose | Why |
|-----------------|---------|-----|
| PyGithub `repo.get_pull()` | PR diff stats | `pr.changed_files`, `pr.additions`, `pr.deletions`; `pr.get_files()` for per-file LOC |
| PyGithub `repo.get_contents()` | Fetch .booty.yml at head_sha | Early validation without clone |
| Pydantic `ConfigDict(extra='forbid')` | Strict schema v1 | Unknown keys fail validation |
| pathspec | max_loc_per_file pathspec | Same as PathRestrictor; gitignore-style |
| get_verifier_repo | App-auth repo access | Already used in checks.py; same for PR fetch |

### Don't Add

| Avoid | Why |
|------|-----|
| Custom diff parsing | PyGithub PR object has aggregates; get_files() has per-file |
| New config loader | Extend load_booty_config; add from_content variant |
| Clone for limit check | Fetch .booty.yml via API; fail fast |

## Architecture Patterns

### Early Validation Flow (Agent PRs Only)

```
process_verifier_job (agent PR)
  → get_verifier_repo(owner, repo_name, installation_id)
  → repo.get_pull(pr_number)  # Diff stats
  → repo.get_contents(".booty.yml", ref=head_sha)  # May 404
  → load_booty_config_from_content(content) or defaults
  → validate schema (strict if schema_version: 1)
  → check_diff_limits(stats, config)  # max_files, max_loc, max_loc_per_file
  → If any fail: edit_check_run failure, return (no clone)
  → Else: clone, load_booty_config(path), execute_tests
```

### Schema v1 Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| schema_version | int | no (default 0) | 1 = strict |
| test_command | str | yes | Existing |
| setup_command | str | no | New |
| timeout_seconds | int | no | Alias for timeout; 300 default |
| max_retries | int | no | Existing |
| allowed_paths | list[str] | no | Builder write scope |
| forbidden_paths | list[str] | no | Hard deny |
| allowed_commands | list[str] | no | Validate only |
| network_policy | enum | no | deny_all \| registry_only \| allow_list |
| labels | dict | no | agent_pr_label, task_label, blocked_label |
| max_files_changed | int | no | Limit override |
| max_diff_loc | int | no | Limit override |
| max_loc_per_file | int | no | Soft limit |
| max_loc_per_file_pathspec | list[str] | no | Where max_loc_per_file applies |

### Limit Defaults (Global)

- max_files_changed: 12
- max_diff_loc: 600
- max_loc_per_file: 250
- max_loc_per_file scope: everywhere except tests/ (pathspec `!tests/**` or equivalent)

### Failure Output Format (per CONTEXT)

```
FAILED: max_files_changed
Observed: 18
Limit: 12
Fix: split PR or raise limit in .booty.yml
```

## Code Examples

### PyGithub PR Diff Stats

```python
repo = get_verifier_repo(owner, repo_name, installation_id, settings)
pr = repo.get_pull(pr_number)
# Aggregates (from PR API):
files_count = pr.changed_files
additions = pr.additions
deletions = pr.deletions
# Per-file (for max_loc_per_file):
for f in pr.get_files():
    # f.filename, f.additions, f.deletions
    pass
```

### Pydantic Strict Schema

```python
from pydantic import BaseModel, ConfigDict

class BootyConfigV1(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal[1] = 1
    test_command: str
    # ...
```

### Fetch File from GitHub

```python
try:
    fc = repo.get_contents(".booty.yml", ref=head_sha)
    content = fc.decoded_content.decode()
except UnknownObjectException:
    content = None  # No .booty.yml, use defaults
```

## Common Pitfalls

### Pitfall 1: timeout vs timeout_seconds
**What goes wrong:** BootyConfig uses `timeout`; schema v1 specifies `timeout_seconds`. Executor expects `config.timeout`.
**How to avoid:** Accept both; map timeout_seconds → timeout internally; executor unchanged.

### Pitfall 2: Limits on non-agent PRs
**What goes wrong:** Enforcing limits on human PRs blocks legitimate large changes.
**How to avoid:** Only run limits check when `job.is_agent_pr` is True.

### Pitfall 3: max_loc_per_file scope
**What goes wrong:** Applying to tests/ catches valid test additions.
**How to avoid:** Default pathspec excludes tests/; configurable per CONTEXT.

## Traceability

| Requirement | Deliverable |
|-------------|-------------|
| VERIFY-06 | limits.py: max_files_changed enforcement |
| VERIFY-07 | limits.py: max_diff_loc enforcement |
| VERIFY-08 | limits.py: max_loc_per_file (pathspec) |
| VERIFY-09 | config.py: schema validation before run |
| VERIFY-10 | config.py: BootyConfig v1 fields |

---
## RESEARCH COMPLETE
