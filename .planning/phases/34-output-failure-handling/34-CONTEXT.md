# Phase 34: Output & Failure Handling - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Architect produces ArchitectPlan output, updates the existing plan comment with a booty-architect section, and handles block cases (structurally unsafe plan). When blocked: update comment, apply agent:architect-review, do NOT trigger Builder, no automatic retries. This phase covers output shape, comment format, and block behavior — not persistence or handoff (Phases 35–36).

</domain>

<decisions>
## Implementation Decisions

### booty-architect section placement and format
- **Placement:** Between sections — after Builder instructions, before collapsed JSON
- **Approved content:** ✓ Approved — Risk: MEDIUM (status + risk level)
- **Rewritten content:** ✎ Rewritten — ambiguous steps clarified (status + short reason)
- **Visibility:** Inline, always visible — not collapsed

### architect_notes visibility
- **When to show:** Operator-relevant notes visible in comment; low-level diagnostics internal only
- **Placement:** Inside booty-architect block, directly after the status line
- **Length handling:** Truncate with expand — first line inline, remainder in `<details>`
- **When empty:** Omit notes entirely — show status line only

### Block notification strategy
- **Location:** Update the same plan comment — single source of truth, avoids thread noise
- **Plan visibility:** Keep plan visible — operators need the failed artifact for manual correction
- **Message format:** Exact phrase "Architect review required — plan is structurally unsafe." plus short reason (e.g. "Steps > 12", "Overreach unresolved")
- **Label timing:** Apply agent:architect-review immediately with block — same flow to prevent race conditions

### Approved vs Rewritten differentiation
- **Visual distinction:** Emoji or status markers — fast visual parsing in long PR threads
- **Layout consistency:** Same layout for Approved and Rewritten — structural consistency improves scanability and automation
- **Rewritten summary:** Brief bullet list of what was altered — operators need to know without diffing the plan
- **Blocked emphasis:** Stronger emphasis — Blocked visually interrupts; treat as exception state rather than normal outcome

### Claude's Discretion
- Exact emoji/symbol choices for Approved (✓), Rewritten (✎), Blocked
- Operator-relevant vs low-level classification for architect_notes
- Blocked visual treatment (blockquote, bold, etc.)
- Threshold for "long" notes (when to truncate to first line + details)

</decisions>

<specifics>
## Specific Ideas

- Single source of truth for plan comment — block updates same comment, not a new one
- Operators need failed plan visible for manual correction
- Blocked = exception state — should visually interrupt, not blend in

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 34-output-failure-handling*
*Context gathered: 2026-02-17*
