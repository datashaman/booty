# Phase 30: Output Delivery - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Post plan to GitHub issue comment and store artifact to `$HOME/.booty/state/plans/<issue_id>.json`. Comment includes human-readable summary (Goal, Risk, Steps, Builder instructions). Output avoids long prose. Implementation clarifies HOW to format and present this output — scope is fixed.

</domain>

<decisions>
## Implementation Decisions

### Comment layout & section order
- Section order: Goal → Risk → Steps → Builder instructions
- Standard markdown headings (`## Goal`, `## Risk`, etc.)
- Moderate spacing between sections
- Raw Plan JSON in `<details>` collapsed by default (hidden until expanded)

### Step list detail
- Per step: action + path + full acceptance criteria inline
- Format: bullet list (`- P1: ...`)
- Keep flat (typically 5–10 steps); no special handling for length unless clearly excessive
- Steps section always visible — not collapsible

### Builder instructions format
- Grouped bullets: `- **Branch:** ...`, `- **Commit:** ...`, `- **PR Title:** ...`, etc.
- `pr_body_outline`: collapsed in its own `<details>` when long
- Equal prominence — same heading level as Goal, Risk, Steps
- Omit empty handoff fields entirely

### JSON placement & visibility
- Position: after Builder instructions (last section before collapsed JSON)
- `<details>` summary label: "Full plan (JSON)"
- Code block: `json` language tag for syntax highlighting
- No explanatory note before the JSON block

### Claude's Discretion
- Exact line breaks and spacing within sections
- Threshold for "long" pr_body_outline (when to collapse)
- Threshold for "excessive" step count (if any special handling)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — standard GitHub markdown, clear operator-focused presentation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 30-output-delivery*
*Context gathered: 2026-02-16*
