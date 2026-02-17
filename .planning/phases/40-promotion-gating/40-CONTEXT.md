# Phase 40: Promotion Gating - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Gate promotion of agent PRs (draft → ready-for-review) on both booty/reviewer and booty/verifier success. Fail-open success counts as success. Non-agent PRs unchanged.

</domain>

<decisions>
## Implementation Decisions

### Reviewer-disabled behavior
- When Reviewer is disabled (no reviewer block in .booty.yml or REVIEWER_ENABLED=false), promotion gate is Verifier-only
- No synthetic booty/reviewer check when disabled
- No "missing check" penalty — treat as if Reviewer doesn't exist

### Waiting state communication
- GitHub Checks UI is sufficient; no extra comment
- Verifier: when Reviewer is enabled and booty/reviewer check is not yet success, do NOT promote — exit with check success but leave PR draft

### Blocked-by-Reviewer feedback
- Reviewer comment is sufficient; no cross-agent messaging
- Do not add "Reviewer blocked" or similar text into Verifier output

### Promotion timing
- Promotion happens when the second check completes successfully and observes the other already-success
- Green-waiting (one check green while the other runs) is acceptable

### Claude's Discretion
- Which component(s) call promote (Verifier only vs both — last-one-wins)
- How to detect Reviewer-enabled state when Verifier runs (config lookup vs check existence)

</decisions>

<specifics>
## Specific Ideas

- Verifier should not promote if reviewer is enabled and reviewer check is not success yet; it should exit with success but leave PR draft

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 40-promotion-gating*
*Context gathered: 2026-02-17*
