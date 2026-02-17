# Phase 33: Validation Rules - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Structural integrity, path consistency, risk accuracy, ambiguity detection, and overreach detection. Architect validates plans against rules, recomputes risk from touch_paths, rewrites ambiguous or overreaching steps when configured, and blocks when structurally unsafe. Rule-driven only (no LLM); target runtime < 5 seconds.

</domain>

<decisions>
## Implementation Decisions

### Empty path handling
- **read/add/edit with no path:** Block — plan fails validation, no approval
- **research action (if added):** Path required — must specify artifact or scope (e.g. "Research X and document in Y")
- **run/verify with path:** Ignore — path is optional; Architect accepts as valid
- **Empty touch_paths** (all run/verify steps): Flag in architect_notes, approve

### Ambiguity triggers
- **Triggers:** Vague acceptance, missing specifics in action, overly broad scope
- **Detection:** Combination — patterns (e.g. "fix", "improve", "as needed") + structure (short acceptance, missing path for edit)
- **When rewrite_ambiguous_steps=false:** Flag only — add to architect_notes, approve
- **Rewrite scope:** Moderate — infer path from clear context when possible; otherwise narrow rewrite only (tighten wording, no aggressive inference)

### Overreach thresholds
- **Repo-wide:** Both path count and directory spread (concrete thresholds to be defined in planning)
- **Multi-domain:** Domain buckets = src/, tests/, docs/, infra/, .github/; touching 2+ domains = multi-domain
- **Speculative architecture:** Keywords (e.g. "refactor architecture", "improve structure", "technical debt") plus scope
- **Response:** Try split into smaller steps first, then narrow scope; block only if neither works

### Rewrite vs block
- **Steps > 12:** Try consolidate (merge related steps to fit ≤12); block if consolidation impossible
- **Validation failure after rewrite:** Retry once (one additional rewrite attempt), then block
- **Minimum steps:** Recommend only — note in architect_notes if plan seems too minimal (e.g. single step); do not block
- **Block message:** Fixed phrase "Architect review required — plan is structurally unsafe." plus short reason (e.g. "Steps > 12", "Overreach unresolved")

### Claude's Discretion
- Exact path-count and directory-spread thresholds for overreach
- Specific keyword patterns for ambiguity and speculative detection
- Consolidation heuristics when merging steps to fit ≤12
- Exact architect_notes phrasing for flags/recommendations

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for rule implementation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 33-validation-rules*
*Context gathered: 2026-02-17*
