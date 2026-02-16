---
phase: 17-cli-documentation
plan: 01
subsystem: cli
tags: [click, governor, github, risk]

provides:
  - booty governor simulate (dry-run decision)
  - booty governor trigger (manual deploy on ALLOW)
  - booty governor status --json
  - simulate_decision_for_cli helper
  - get_risk_paths for --show-paths
affects: [17-02]

key-files:
  modified: [src/booty/cli.py, src/booty/release_governor/handler.py, src/booty/release_governor/risk.py]

key-decisions:
  - "Unblock hints built from config approval_mode (environment/label/comment)"
  - "Repo inference from git remote get-url origin"
  - "GITHUB_TOKEN required for simulate/trigger; clear error on missing"

completed: 2026-02-16
---

# Phase 17 Plan 01: Governor CLI Summary

**Governor CLI: simulate, trigger, status --json — dry-run decision, manual deploy trigger, machine-readable output**

## Performance

- **Tasks:** 4
- **Files modified:** 3 (cli.py, handler.py, risk.py)

## Accomplishments

- `simulate_decision_for_cli` in handler.py — computes Decision + risk_paths without webhook
- `get_risk_paths` in risk.py — returns filenames matching high/medium risk for --show-paths
- `booty governor simulate [--sha] <sha>` — dry-run decision; --show-paths, --json; fails clearly when GITHUB_TOKEN missing
- `booty governor trigger [--sha] <sha>` — dispatches deploy on ALLOW; exit 1 on HOLD with unblock hint
- `booty governor status --json` — machine-readable ReleaseState

## Files Modified

- `src/booty/cli.py` — governor status --json, simulate, trigger, _infer_repo_from_git, _unblock_hints
- `src/booty/release_governor/handler.py` — simulate_decision_for_cli
- `src/booty/release_governor/risk.py` — get_risk_paths

## Decisions Made

- Repo inference from `git remote get-url origin` with GitHub URL parsing
- Unblock hints vary by approval_mode (environment → RELEASE_GOVERNOR_APPROVED; label → add label; comment → comment command)
- State dir uses get_state_dir() as-is (no workspace override for state)

## Deviations from Plan

None — plan executed as written.

## Issues Encountered

None

---
*Phase: 17-cli-documentation*
*Completed: 2026-02-16*
