# Memory Agent

Stores high-value system events (incidents, governor holds, verifier failures, reverts) as durable records and surfaces related history in PR comments and incident issues. Informational only — no outcomes are blocked or altered.

## Overview

The Memory Agent:

- **Ingests** events from Observability (Sentry incidents), Governor (holds, deploy failures), Security (blocks), Verifier (failures), and revert detection on main
- **Stores** records in `memory.jsonl` in the configured state dir (default `~/.booty/state`)
- **Surfaces** up to 3 related matches in PR comments after Verifier completes, Governor HOLD details, and Observability incident issue bodies
- **Retention** keeps last 90 days by default (configurable)

## Configuration

Add a `memory` block to `.booty.yml` (schema_version 1):

```yaml
schema_version: 1
test_command: pytest

memory:
  enabled: true
  retention_days: 90
  max_matches: 3
  comment_on_pr: true
  comment_on_incident_issue: true
```

| Key | Default | Description |
|-----|---------|-------------|
| `enabled` | `true` | Enable memory ingestion and surfacing |
| `retention_days` | `90` | Keep records within this window |
| `max_matches` | `3` | Max matches per PR comment |
| `comment_on_pr` | `true` | Post "Memory: related history" on PRs |
| `comment_on_incident_issue` | `true` | Append "Related history" to Observability issue bodies |

**Env overrides:** `MEMORY_ENABLED`, `MEMORY_RETENTION_DAYS`, `MEMORY_MAX_MATCHES`, `MEMORY_STATE_DIR`

## CLI reference

### booty memory status

Show memory state (enabled, record count, retention). Requires `.booty.yml` with memory block.

```bash
booty memory status
booty memory status --json
```

| Option | Description |
|--------|-------------|
| `--workspace PATH` | Workspace dir (default: `.`) |
| `--json` | Machine-readable JSON output |

**Output when disabled:**
```
Memory disabled
```

**Output when enabled:**
```
enabled: true
records: 42
retention_days: 90
```

### booty memory query

Query related history by PR number or commit SHA. Requires `GITHUB_TOKEN`.

```bash
booty memory query --pr 123 --repo owner/repo
booty memory query --sha abc123def --repo owner/repo
booty memory query --pr 123 --repo owner/repo --json
```

| Option | Description |
|--------|-------------|
| `--pr N` | PR number (mutually exclusive with `--sha`) |
| `--sha SHA` | Commit SHA; resolves to PR for file paths |
| `--repo owner/repo` | Required when not in a git repo |
| `--workspace PATH` | Workspace dir (default: `.`) |
| `--json` | Machine-readable JSON output |

Provide exactly one of `--pr` or `--sha`.

**Output (human-readable):**
```
- **incident** (2024-01-15) — Database timeout https://github.com/o/r/issues/42
- **governor_hold** (2024-01-14) — Held deploy
```

**Output (no matches):**
```
(no related history)
```

### booty memory ingest revert

Store a revert record manually (e.g. for reverts not detected via push):

```bash
booty memory ingest revert --repo owner/repo --sha abc123 --reverted-sha def456
```

## State directory

- Default: `~/.booty/state` (or `./.booty/state` if `HOME` unset)
- Override: `MEMORY_STATE_DIR` env var
- Records: `memory.jsonl` (append-only, one JSON object per line)

---
*See [github-app-setup.md](github-app-setup.md) for webhook events required for Memory.*
