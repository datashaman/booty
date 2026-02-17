# Phase 39: Review Engine - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Diff-focused LLM prompt, structured output schema, and block_on config mapping. The engine evaluates engineering quality (maintainability, overengineering, duplication, test quality, naming/API, architectural drift) and produces APPROVED / APPROVED_WITH_SUGGESTIONS / BLOCKED decisions. Quality only — no lint, tests reruns, or style nitpicks.

</domain>

<decisions>
## Implementation Decisions

### Rubric structure

- Fixed rubric with 6 evaluation categories, each producing:
  - `grade`: PASS | WARN | FAIL
  - `findings[]`: { summary, detail, paths[], line_refs[]?, suggestion? }
  - `confidence`: low | med | high

- Mapping to block_on (4 blockers):
  - overengineering ⇐ category: Overengineering
  - poor_tests ⇐ category: Tests
  - duplication ⇐ category: Duplication
  - architectural_regression ⇐ category: Architectural drift

- Non-blocking categories: Maintainability, Naming/API — can generate WARN/FAIL but never block.

- Overall decision logic:
  - If any enabled blocker category has grade FAIL → BLOCKED
  - Else if any category has WARN or FAIL → APPROVED_WITH_SUGGESTIONS
  - Else → APPROVED

### Block-on behavior

- Only the 4 block_on categories can block.
- Maintainability and Naming/API can never block, regardless of severity.
- block_on empty or missing → Reviewer never blocks; max decision is APPROVED_WITH_SUGGESTIONS.
- Partial config: only configured categories participate in blocking; all 6 categories still produce findings.

### Comment presentation

Single updatable PR comment within `<!-- booty-reviewer -->` ... `<!-- /booty-reviewer -->`:

1. **Header line:** Reviewer: APPROVED | APPROVED_WITH_SUGGESTIONS | BLOCKED
2. **Short rationale:** Blocking: duplication, poor_tests (only if BLOCKED)
3. **Sections** grouped by category, in this order:
   - Overengineering
   - Architectural drift
   - Tests
   - Duplication
   - Maintainability
   - Naming/API
4. **Each section:**
   - Status: PASS / WARN / FAIL
   - Up to 3 bullets per category; each bullet: path(s), what's wrong, concrete improvement
5. **Overflow:** If more than 3 findings in a category: add (+N more) and keep the highest-impact ones.

No line-by-line annotations; review-level, not lint-level.

### Prompt context

**Provide the LLM:**
- Unified diff (full patch) + file list changed
- PR title + body
- Base SHA and head SHA
- For each changed file: file type and whether it's under tests/ (path prefix)
- Optional: linked issue title/body if PR references an issue (cheap context)

**Do not include:**
- Full repo tree
- Full file contents beyond diff
- Test logs, lint output, security output — explicitly instruct the model to ignore these

</decisions>

<specifics>
## Specific Ideas

- Keep output review-level, not lint-level — no line-by-line annotations.
- Optional linked issue context is "cheap" and worth including when available.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 39-review-engine*
*Context gathered: 2026-02-17*
