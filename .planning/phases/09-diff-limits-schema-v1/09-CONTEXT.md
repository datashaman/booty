# Phase 9: Diff Limits + .booty.yml Schema v1 - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Enforce diff limits on PRs and validate extended .booty.yml schema v1. Verifier rejects PRs exceeding limits and fails check on invalid config. Limits apply to agent PRs only. Schema v1 adds new fields; backward compat: repos without schema_version use v0 (existing BootyConfig).

</domain>

<decisions>
## Implementation Decisions

### Limit defaults and sources
- Both: global defaults with per-repo override in .booty.yml
- When absent: always apply global defaults (limits always on)
- Defaults: `max_files_changed: 12`, `max_diff_loc: 600`, `max_loc_per_file: 250`
- `max_loc_per_file` is soft — enforced outside `tests/` only
- Reasoning: forces decomposition early; prevents architectural spillover
- Limits apply to agent PRs only (same scope as other Verifier gates)

### Check failure presentation
- Terse title + expandable details — fast scan, depth on demand
- Never expose raw validation alone; human-friendly message + full error in details
- Report all failures in one pass; batch failures reduce repair cycles
- Order: 1) Schema (blocking), 2) Safety limits, 3) Structural checks
- Stop execution after reporting
- Always include a repair hint
- Format: mechanical, not conversational
  ```
  FAILED: max_files_changed
  Observed: 18
  Limit: 12
  Fix: split PR or raise limit in .booty.yml
  ```

### max_loc_per_file pathspec design
- Single global `max_loc_per_file` with optional pathspec defining where it applies
- Default scope: everywhere except `tests/` (gitignore-style pathspec)
- Pathspec format: same as `protected_paths` — gitignore-style with `**`
- Single rule — either include or exclude (no per-path limit mappings)
- Violations fail the check but are reported separately from hard limits (max_files_changed, max_diff_loc)

### Schema v1 strictness and field semantics
- **Strict:** unknown keys fail validation (config drift = operational risk)
- **Path semantics — keep separate:**
  - `allowed_paths` → where Builder may write
  - `forbidden_paths` → hard deny for agent edits
  - `protected_paths` → Booty self-protection (different threat class)
- **labels** — agent control-plane labels (routing primitives, not decorative):
  - `agent_pr_label`: agent:builder
  - `task_label`: agent-task
  - `blocked_label`: agent-blocked
- **network_policy** — include now with enum: `deny_all` | `registry_only` | `allow_list`
  - Validate only; no enforcement yet
  - Reasoning: schema stability > feature timing; adding later is breaking change

### Claude's Discretion
- Exact pathspec default for max_loc_per_file scope (e.g. `!tests/**` vs `**/*` with exclusion)
- Check output layout/formatting details (GitHub Checks API constraints)
- Field naming alignment (timeout vs timeout_seconds in existing BootyConfig)

</decisions>

<specifics>
## Specific Ideas

- Mechanical failure output pattern: FAILED / Observed / Limit / Fix
- "Fast scan + depth on demand" — operator efficiency
- Schema stability over feature timing for network_policy

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-diff-limits-schema-v1*
*Context gathered: 2026-02-15*
