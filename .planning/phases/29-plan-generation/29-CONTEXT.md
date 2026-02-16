# Phase 29: Plan Generation - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

LLM produces valid Plan JSON from normalized PlannerInput (from Phase 28). Risk classification is applied via deterministic rules. Plan schema (steps, handoff_to_builder, touch_paths) is fixed. Output delivery (issue comment, storage) is Phase 30; idempotency is Phase 31.

</domain>

<decisions>
## Implementation Decisions

### Step granularity and action types

- **Multiple steps per logical unit** — Prevents hidden work; improves Builder determinism
- **Explicit read only when heavy or cross-cutting** — Avoid plan bloat; fold routine reads into edit steps
- **Any exploratory step must declare an artifact** — Forces epistemic closure; no vague "look into…" steps
- **Separate run and verify** — Command ≠ acceptance; keeps execution auditable; distinct steps for running vs checking outcome

### Risk classification

- **Highest wins, surface drivers** — When touch_paths span HIGH/MEDIUM/LOW, use highest; expose which path(s) drove the risk_level
- **Purely rules-based** — LLM never overrides; risk derived deterministically from touch_paths
- **Exclude docs/README from risk** — Do not count docs/*, README.md etc. toward risk classification
- **Empty touch_paths → HIGH** — Default to HIGH when no paths declared (unknown scope)

### touch_paths and unknown paths

- **Prefer exact paths; globs when inherently plural** — Use globs (e.g. `tests/**/*auth*.py`) only when the file set is inherently multiple files
- **Convention for new files** — Require plausible path; LLM picks convention (e.g. `tests/test_auth.py`) for "add new file" steps
- **touch_paths = union of step paths** — Must align; touch_paths derived from read/edit/add step paths only
- **Only read/edit/add** — Exclude run command scope; do not infer touch_paths from `run pytest tests/` etc.

### handoff_to_builder specificity

- **pr_body_outline: mixed** — Bullets for technical items, short prose for context
- **branch_name_hint: strict convention** — e.g. `issue-123-short-slug`; Builder follows format
- **commit_message_hint: single line** — Conventional format, e.g. `fix: add auth validation`
- **pr_title: include issue ref when available** — e.g. `[#123] Add validation to auth flow`

### Claude's Discretion

- Exact branch naming convention format (e.g. `issue-{n}-{slug}` vs `fix/{slug}`)
- Exact glob syntax and when "inherently plural" applies
- How to surface risk drivers (metadata field, comment text, etc.)
- LLM prompt structure and few-shot examples

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Schema already defined in Phase 27 (`src/booty/planner/schema.py`). Requirements PLAN-05 through PLAN-12, PLAN-19 through PLAN-21, PLAN-25 apply.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 29-plan-generation*
*Context gathered: 2026-02-16*
