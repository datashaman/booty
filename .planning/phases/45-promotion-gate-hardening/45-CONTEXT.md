# Phase 45: Promotion Gate Hardening - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Harden promotion gating so Verifier promotes only when all gates pass: Verifier success AND (Reviewer success OR fail-open OR disabled), and for plan-originated PRs with Architect enabled, Architect approval. Ensure Verifier-only promote, deterministic second-finisher, and idempotent promote. Requirements: PROMO-01 through PROMO-05.

</domain>

<decisions>
## Implementation Decisions

### Plan-originated PR detection
- **Definition:** PR has an issue link AND that issue has a `<!-- booty-plan -->` marker (plan comment)
- **Fallback:** If plan comment is edited/removed, fall back to Architect artifact on disk if present
- **Compat-path PRs:** Any PR from an issue with a plan is plan-originated (including compat-path where Builder used Planner plan without Architect)
- **Architect disabled:** Still detect plan-originated for logging/metrics only; Architect gate is skipped

### Architect approval verification at promote-time
- **Sources:** Check both GitHub plan comment (Architect section) and Architect artifact on disk — belt-and-suspenders
- **Source of truth:** GitHub (plan comment) wins; disk artifact is advisory
- **Fail-open:** No — Architect gate is strict; no approval means no promote
- **Indeterminate:** If we cannot determine plan-originated (e.g. missing issue link), treat as not plan-originated and skip Architect gate

### Idempotency (PROMO-05)
- **Strategy:** Re-fetch PR draft state before promote; if not draft (already ready), skip
- **Already-ready handling:** Log `pr_already_ready`, treat as success
- **PR missing/inaccessible on re-fetch:** Treat as no-op, log and return (no raise/retry)
- **Location:** Idempotent check lives inside `promote_to_ready_for_review`, not in Verifier

### Gate check order and logging
- **Order:** Check Reviewer first, then Architect
- **Reviewer blocking:** Keep current behavior (`promotion_waiting_reviewer`)
- **Architect blocking:** Log `promotion_waiting_architect`
- **Both blocking:** Log both reasons

### Claude's Discretion
- Exact implementation of `<!-- booty-plan -->` detection (parsing, comment structure)
- How to extract Architect approval from plan comment
- Exact log message format for `pr_already_ready` and "PR missing" no-op

</decisions>

<specifics>
## Specific Ideas

- Plan marker: `<!-- booty-plan -->` in issue comments
- Architect approval lives in plan comment Architect section; disk artifact is advisory fallback
- promotion_waiting_reviewer (existing); promotion_waiting_architect (new)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 45-promotion-gate-hardening*
*Context gathered: 2026-02-17*
