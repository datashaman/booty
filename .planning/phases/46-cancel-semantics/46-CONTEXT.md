# Phase 46: Cancel Semantics - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Verifier cooperative cancel: when a new push (new head_sha) for the same PR arrives, the prior Verifier run is cancelled. Mirror ReviewerQueue's request_cancel pattern. Verifier runner checks cancel_event at phase boundaries; superseded run exits with conclusion=cancelled. Requirements: DEDUP-03, DEDUP-05.

</domain>

<decisions>
## Implementation Decisions

### Phase Boundary Locations

- **5–6 cancel check points:** Entry, before clone, after setup, after install, after compile/import, before tests, before promote
- **Cancelled before check run created:** Create check run with conclusion=cancelled (do not silent exit)
- **Check cancel before schema/limits early exits:** Yes — check before every early return in config validation
- **"Before promote" placement:** Check cancel before promotion-gate logic (before we evaluate Reviewer/Architect gates)

### Superseded Check Run Text

- **Summary:** Match Reviewer: "Cancelled — superseded by new push"
- **Title:** Explicit: "Booty Verifier — Cancelled"
- **Queued-then-cancelled:** Use same superseded summary (no different text for "never started")
- **Consistency:** Match Reviewer wording exactly — same summary across agents

### Best-Effort Window

- **During execute_tests:** Accept that we cannot cancel mid-test — best-effort is sufficient
- **No mid-test cancel complexity:** Don't add subprocess termination or chunked checks
- **Worst case:** Let run complete, mark cancelled at next check (after tests)
- **Responsiveness:** Before next step is enough — no requirement for cancel within seconds

### Early-Exit Paths

- **All early exits:** Check cancel before every early return (schema, limits, config, etc.)
- **Check run already in_progress or failure:** If cancel arrives, overwrite to conclusion=cancelled
- **Entry point:** Check cancel at very top of process_verifier_job, before verifier_enabled
- **After failure edit:** Check cancel even after edit_check_run(conclusion="failure") — overwrite to cancelled if cancel_event is set

### Claude's Discretion

- Exact placement of each check point within the runner flow
- Order of operations when overwriting failure → cancelled

</decisions>

<specifics>
## Specific Ideas

- "Booty Verifier — Cancelled" for title when superseded (explicit, not generic)
- Mirror Reviewer wording: "Cancelled — superseded by new push" for summary
- Consistency across Verifier and Reviewer agents for superseded UX

</specifics>

<deferred>
## Deferred Ideas

- Mid-test cancel (subprocess termination during execute_tests) — explicitly out of scope; best-effort accepted
- Security cooperative cancel — DEDUP-06 in Future Requirements (optional)

</deferred>

---

*Phase: 46-cancel-semantics*
*Context gathered: 2026-02-17*
