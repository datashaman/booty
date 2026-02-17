---
phase: 42-event-router
plan: 03
subsystem: router
tags: [webhook, routing, event_skip, canonical]

requires:
  - phase: 42-01
    provides: [events, normalizer]
  - phase: 42-02
    provides: [should_run, enabled]
provides:
  - Canonical route_github_event
  - Webhook delegates issues, pull_request, workflow_run to router
  - event_skip structured logging
  - booty.github.repo_config for shared config loading
affects: [43, 44]

tech-stack:
  added: [booty.github.repo_config]
  patterns: [single dispatch, normalize→should_run→enqueue]

key-files:
  created: [src/booty/router/router.py, src/booty/github/repo_config.py]
  modified: [src/booty/webhooks.py, src/booty/router/__init__.py]

key-decisions:
  - check_run, push, sentry remain in webhooks (not agent enqueue events)
  - background_tasks passed to router for governor hold surfacing

patterns-established:
  - "Webhook: verify → parse → route_github_event for issues/PR/workflow_run"

duration: 15min
completed: 2026-02-17
---

# Phase 42 Plan 03: Router + Webhook Wire Summary

**Canonical router; webhook delegates issues, pull_request, workflow_run. ROUTE-01 through ROUTE-05 complete.**

## Performance

- **Duration:** 15 min
- **Completed:** 2026-02-17
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments

- router/router.py with route_github_event for issues, pull_request, workflow_run
- Webhook refactored: thin dispatch + check_run + push + sentry
- event_skip structured logging (agent, repo, event_type, reason)
- booty.github.repo_config with repo_from_url, load_booty_config_for_repo
- All enqueue paths use should_run

## Task Commits

1. **Task 1: Create router/router.py** - `9484603` (feat)
2. **Task 2: Refactor webhooks** - `2293b88` (feat)

## Deviations from Plan

None - plan executed as written.

## Next Phase Readiness

- Phase 42 Event Router complete
- ROUTE-01 through ROUTE-05 verified
- Ready for Phase 43 Dedup Alignment

---
*Phase: 42-event-router*
*Completed: 2026-02-17*
