# Phase 46: Cancel Semantics — Research

## RESEARCH COMPLETE

**Gathered:** 2026-02-17
**Status:** Ready for planning

---

## Executive Summary

Phase 46 adds cooperative cancel to Verifier: when a new push (new head_sha) for the same PR arrives, the prior Verifier run is cancelled. Mirror ReviewerQueue's request_cancel pattern. VerifierQueue gains `request_cancel` and `_cancel_events`; VerifierJob gains `cancel_event`; Verifier runner checks `cancel_event` at 5–6 phase boundaries; superseded run exits with `conclusion=cancelled`. Requirements: DEDUP-03, DEDUP-05.

---

## Reference: ReviewerQueue Cancel Pattern

**File:** `src/booty/reviewer/queue.py`

- `_cancel_events: dict[tuple[str, int], asyncio.Event]` — keyed by `(repo_full_name, pr_number)`
- `request_cancel(repo_full_name, pr_number)` — if key exists, `event.set()`
- `enqueue`: call `request_cancel` before enqueue; create new `asyncio.Event`, store in `_cancel_events[(repo, pr)]`, attach `job.cancel_event = event`; on put success, mark_processed; on failure (timeout), pop `_cancel_events` and discard processed
- Worker: `try/finally` clears `_cancel_events[(repo, pr)]` when job completes

**File:** `src/booty/reviewer/job.py`

- `cancel_event: asyncio.Event | None = None` in ReviewerJob dataclass

**File:** `src/booty/reviewer/runner.py`

- Check at entry: `if getattr(job, "cancel_event", None) and job.cancel_event.is_set(): return` (before creating check run — Reviewer returns without creating; Verifier context says create check run with cancelled for queued-then-cancelled)
- Check after config load, before create_check_run
- Check after create_check_run + edit in_progress: if cancelled, `edit_check_run(conclusion="cancelled", output={"title":"Booty Reviewer","summary":"Cancelled — superseded by new push"})`, return

---

## Current Verifier State

### VerifierQueue (`src/booty/verifier/queue.py`)

- `_queue`, `_processed`, `_processed_order`, `_worker_tasks`
- `is_duplicate`, `mark_processed`, `enqueue`
- No `_cancel_events`, no `request_cancel`
- `enqueue` does NOT call request_cancel; does NOT attach cancel_event to job

### VerifierJob (`src/booty/verifier/job.py`)

- No `cancel_event` field

### Verifier Runner (`src/booty/verifier/runner.py`)

- `process_verifier_job` has many phase boundaries and early returns
- No cancel checks anywhere

### Router (`src/booty/router/router.py`)

- Verifier enqueue: `verifier_queue.is_duplicate(...)` then `verifier_queue.enqueue(job)`
- Router has `internal.full_name`, `internal.pr_number`, `internal.head_sha`
- New head_sha for same PR = different dedup key, so NOT deduplicated; enqueue succeeds. Prior run (if in-flight) is NOT signalled to cancel.

---

## Phase Boundaries in process_verifier_job (Exact Locations)

Per 46-CONTEXT decisions:

| # | Location | Line(s) approx | Action on cancel |
|---|-----------|----------------|------------------|
| 1 | Entry | ~200 | Check before verifier_enabled. If cancelled before check run: create check run with conclusion=cancelled, return |
| 2 | Before clone | ~220 | After create_check_run; before agent PR schema/limits. If cancelled: edit to cancelled, return |
| 3 | Before agent config validation early exits | ~224–267 | Check before each early return (schema, limits) |
| 4 | After workspace acquired, before setup | ~275–280 | After edit in_progress |
| 5 | After setup, before install | ~365 | After setup_command success |
| 6 | After install, before compile/import | ~391 | After install_command success |
| 7 | After compile/import, before execute_tests | ~350 | Before `execute_tests(config.test_command...)` |
| 8 | After tests, before promote | ~394 | Before reviewer_check_success / architect gates |
| 9 | After failure edit | — | If edit_check_run(conclusion="failure") and cancel arrives, overwrite to cancelled |
| 10 | Exception handler | ~446 | If conclusion=failure and cancel_event set, overwrite to cancelled |

Context: "5–6 cancel check points" — can consolidate some; key is coverage of entry, pre-clone, post-setup, post-install, pre-tests, pre-promote.

---

## Superseded Check Run Text (46-CONTEXT)

- **Title:** "Booty Verifier — Cancelled"
- **Summary:** "Cancelled — superseded by new push"
- Match Reviewer wording exactly

---

## Best-Effort Semantics

- No mid-test cancel (execute_tests runs to completion)
- Check at phase boundaries only
- If cancel arrives during tests, handle at next check (after tests, before promote)
- Queued-then-cancelled: create check run with status=completed, conclusion=cancelled (do NOT silent return)

---

## Files to Modify

1. **src/booty/verifier/job.py** — Add `cancel_event: asyncio.Event | None = None`
2. **src/booty/verifier/queue.py** — Add `_cancel_events`, `request_cancel`; in `enqueue`: call `request_cancel`, create event, attach to job, clear in worker `finally`
3. **src/booty/verifier/runner.py** — Add cancel checks at all phase boundaries; use `edit_check_run(conclusion="cancelled", output={"title":"Booty Verifier — Cancelled","summary":"Cancelled — superseded by new push"})`
4. **src/booty/main.py** (or wherever verifier worker runs) — Ensure worker clears `_cancel_events` in finally (VerifierQueue.worker pattern must match ReviewerQueue)

---

## Worker Cleanup Pattern

ReviewerQueue worker (from 38-03-PLAN):

```python
try:
    await process_fn(job)
finally:
    self._cancel_events.pop((repo_full_name, job.pr_number), None)
    self._queue.task_done()
```

VerifierQueue.worker currently has `self._queue.task_done()` in finally but no `_cancel_events` — add same cleanup when we add _cancel_events.

---

## Recommendations for Planning

1. **Plan 46-01:** VerifierQueue request_cancel + VerifierJob cancel_event + enqueue wiring (Wave 1)
2. **Plan 46-02:** Verifier runner cancel checks at all phase boundaries (Wave 2, depends on 01)

Alternative: Single plan if tightly coupled (queue + runner both needed for cancel to work). Context suggests 2 plans: queue changes first (foundation), runner changes second (consumer).

---

## Open Decisions (Claude's Discretion)

- Exact placement of each check point within runner (46-CONTEXT gives 5–6; map precisely to code structure)
- Order when overwriting failure → cancelled (check cancel after edit_check_run(failure))
