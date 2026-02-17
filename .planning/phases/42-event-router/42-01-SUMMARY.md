---
phase: 42-event-router
plan: 01
subsystem: router
tags: [dataclass, webhook, github, normalization]

requires: []
provides:
  - Internal event structs (IssueEvent, PREvent, WorkflowRunEvent)
  - GitHub → internal normalizer with typed conversion
  - router package with single entry point for normalize()
affects: [42-02, 42-03]

tech-stack:
  added: []
  patterns: [dataclass event structs, raw_payload preservation]

key-files:
  created: [src/booty/router/events.py, src/booty/router/normalizer.py, src/booty/router/__init__.py]
  modified: []

key-decisions:
  - TRIGGER_LABEL from get_settings() for is_agent_pr detection
  - raw_payload kept for agent-specific parsing

patterns-established:
  - "Event structs carry action, delivery_id, sender + event-specific routing fields"
  - "normalize(event_type, payload, delivery_id) as single dispatch entry point"

duration: 5min
completed: 2026-02-17
---

# Phase 42 Plan 01: Internal Events + Normalizer Summary

**Typed internal event structs and GitHub→internal normalizer before enqueue. ROUTE-01 complete.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-17
- **Completed:** 2026-02-17
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- IssueEvent, PREvent, WorkflowRunEvent dataclasses with routing fields + raw_payload
- normalize_issue_event, normalize_pr_event, normalize_workflow_run_event
- Public normalize(event_type, payload, delivery_id) dispatching by event_type
- router package exports events and normalizer functions

## Task Commits

1. **Task 1: Create router/events.py** - `59e1c92` (feat)
2. **Task 2: Create router/normalizer.py** - `822c4b2` (feat)
3. **Task 3: Router package init** - `dc78554` (feat)

**Plan metadata:** (to be committed)

## Files Created/Modified

- `src/booty/router/events.py` - IssueEvent, PREvent, WorkflowRunEvent dataclasses
- `src/booty/router/normalizer.py` - GitHub payload → internal event conversion
- `src/booty/router/__init__.py` - Package exports

## Decisions Made

- TRIGGER_LABEL from get_settings() for is_agent_pr (per plan: pass as arg or get_settings)
- WorkflowRunEvent workflow_run_id accepts int|str for GitHub API flexibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

- events.py and normalizer.py ready for should_run (42-02) and router (42-03)
- ROUTE-01: normalization layer exists; internal events typed

---
*Phase: 42-event-router*
*Completed: 2026-02-17*
