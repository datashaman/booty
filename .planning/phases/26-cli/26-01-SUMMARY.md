---
phase: 26-cli
plan: 01
subsystem: cli
tags: click, memory, booty-cli

requires:
  - phase: 24-lookup
    provides: memory.query, within_retention
  - phase: 22-memory-foundation
    provides: store.read_records, get_memory_state_dir, config
provides:
  - booty memory status — enabled, record count, retention_days (MEM-27)
  - booty memory query --pr/--sha with --json (MEM-28)
affects: []

tech-stack:
  added: []
  patterns: Click subcommand with --json, config loading via load_booty_config

key-files:
  created: [tests/test_memory_cli.py]
  modified: [src/booty/cli.py]

key-decisions:
  - "Commands named explicitly: @memory.command('status'), @memory.command('query') for clean UX"

patterns-established:
  - "Memory status: load config → get_memory_config → apply_memory_env_overrides → read_records + within_retention"
  - "Memory query: mutually exclusive --pr/--sha, GITHUB_TOKEN required, format_matches_for_pr for human output"

duration: ~15min
completed: 2026-02-16
---

# Phase 26: CLI Summary

**booty memory status and query subcommands — operators can inspect memory state and query related history by PR or SHA per MEM-27, MEM-28**

## Performance

- **Duration:** ~15 min
- **Tasks:** 3
- **Files modified:** 2 (cli.py, test_memory_cli.py)

## Accomplishments

- `booty memory status` prints enabled, records, retention_days; handles disabled cleanly; supports `--json`
- `booty memory query --pr N` and `--sha SHA` resolve paths from GitHub API, run memory.query, output human or JSON
- GITHUB_TOKEN required for query; mutual exclusivity of --pr/--sha enforced
- 11 unit tests covering status (disabled/enabled/JSON) and query (mutex, token, repo, output format)

## Task Commits

1. **Task 1–2: booty memory status and query** — `c49eca6` (feat)
2. **Task 3: memory CLI unit tests** — `a2961c2` (test)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `src/booty/cli.py` — Added memory_status and memory_query commands
- `tests/test_memory_cli.py` — 11 tests for status and query

## Decisions Made

- Used explicit command names `@memory.command("status")` and `@memory.command("query")` so UX is `booty memory status` (not `booty memory memory-status`)
- Reused `format_matches_for_pr` from surfacing for human-readable query output

## Deviations from Plan

None — plan executed as written.

## Issues Encountered

None

---
*Phase: 26-cli*
*Completed: 2026-02-16*
