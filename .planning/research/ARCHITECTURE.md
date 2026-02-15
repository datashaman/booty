# Architecture Research: Verifier Agent

**Domain:** Verifier integration with Booty
**Researched:** 2026-02-15
**Confidence:** HIGH

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GitHub (Webhook + Checks)                         │
│  pull_request (opened, synchronize) ──► Booty webhook                    │
│  check run booty/verifier ◄────────── Verifier posts result               │
├─────────────────────────────────────────────────────────────────────────┤
│                            Booty Application                            │
│  ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐  │
│  │ Webhook Handler │     │ Verifier Agent   │     │ Builder Agent   │  │
│  │ (extended)      │────►│ (NEW)            │     │ (existing)      │  │
│  │ + pull_request  │     │ - Clone PR head  │     │ - issue → PR    │  │
│  └─────────────────┘     │ - Validate config│     └─────────────────┘  │
│                          │ - Run tests      │                           │
│                          │ - Post check run│                           │
│                          └────────┬────────┘                           │
│                                   │                                     │
│  ┌────────────────────────────────┼────────────────────────────────┐   │
│  │ Shared: test_runner, git ops   │                                │   │
│  │ prepare_workspace (clone), execute_tests(), load_booty_config()   │   │
│  └────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|-----------------|
| **Webhook (extended)** | Accept `pull_request` events; route to Verifier queue | Add branch for `event_type == "pull_request"` and `action in ("opened", "synchronize")` |
| **Verifier worker** | Process PR: clone, validate, test, post check | New `process_pr_verification()` async; uses VerifierJob |
| **VerifierJob** | PR context: repo, head_sha, pr_number, labels, author | Similar to Job; different payload shape |
| **Check run poster** | Create/update `booty/verifier` check via Checks API | New module `booty/github/checks.py`; uses GitHub App auth |
| **Diff limit checker** | Enforce max_files, max_loc, max_loc_per_file | pathspec for per-file limits; PR stats for totals |
| **Import/compile detector** | AST parse changed files; validate imports | Extend or reuse test_runner import validation; run setup_command first |

## Recommended Project Structure

```
src/booty/
├── github/
│   ├── pulls.py      # existing
│   ├── comments.py  # existing
│   └── checks.py    # NEW: create_check_run, update_check_run (App auth)
├── verifier/
│   ├── __init__.py
│   ├── job.py       # VerifierJob dataclass
│   ├── runner.py    # process_pr_verification() orchestration
│   ├── limits.py    # diff limit enforcement
│   └── imports.py   # hallucinated import detection
├── webhooks.py      # EXTEND: pull_request handling
├── test_runner/     # REUSE: config, executor
└── ...
```

## Data Flow

### Verifier Request Flow

```
GitHub pull_request webhook
    │
    ▼
Webhook handler (verify HMAC) ──► not duplicate? ──► Enqueue VerifierJob
    │
    ▼
Verifier worker picks job
    │
    ├─► Clone repo at PR head_sha (clean env)
    ├─► Load .booty.yml (validate schema)
    ├─► Check diff limits (PR stats)
    ├─► Detect import/compile issues (AST + setup run)
    ├─► Run tests (execute_tests)
    │
    ▼
Post check run: conclusion = success | failure
    │
    ├─► If agent PR: Check blocks merge (required)
    └─► If human PR: Check informational only
```

### Authentication Split

| Path | Auth | Purpose |
|------|------|---------|
| Builder (issues → PR) | PAT (GITHUB_TOKEN) | Issues, PR creation, comments |
| Verifier (PR → check) | GitHub App | Checks API only; `booty/verifier` |

## Integration Points

### With Existing Codebase

| Existing | Integration |
|----------|-------------|
| **prepare_workspace** | Verifier needs variant: clone at `head_sha` (PR branch), not `base` + new branch. New `prepare_verification_workspace(repo_url, head_ref)` |
| **execute_tests** | Direct reuse; same `test_command`, `timeout` from .booty.yml |
| **load_booty_config** | Extend BootyConfig for schema v1; validate before run |
| **Job queue** | Verifier can use same queue (different job type) or separate; same worker pool pattern |

### With GitHub

| Service | Pattern | Notes |
|---------|---------|-------|
| Webhook | One endpoint `/webhooks/github`; branch on `X-GitHub-Event` | Add `pull_request` handling |
| Checks API | `repo.create_check_run()` → `check_run.edit()` | Requires GitHub App |
| Branch protection | User configures "Require status checks: booty/verifier" | Out of Booty scope; docs |

## Build Order

1. **GitHub App auth** — Add Settings for `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`; `booty/github/checks.py` with App-authenticated `create_check_run`
2. **pull_request webhook** — Extend webhooks.py; enqueue VerifierJob
3. **Verifier runner** — Clone at head, load config, run tests, post check
4. **Diff limits** — Add to runner; enforce before test run
5. **Import/compile detection** — Add to runner; run setup_command, capture early failures
6. **.booty.yml schema v1** — Extend BootyConfig; backward-compatible defaults

## Sources

- PROJECT.md, existing webhooks.py, test_runner
- GitHub webhook events (pull_request)
- PyGithub Checks API

---
*Architecture research for: Verifier agent (Booty v1.2)*
*Researched: 2026-02-15*
