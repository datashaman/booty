# Phase 6: PR Promotion - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Draft PRs are automatically promoted to ready-for-review when all validation passes (tests + linting). Self-modification PRs always remain draft. Promotion failures are handled gracefully — PR stays draft, job continues, visibility via comment or logs.

</domain>

<decisions>
## Implementation Decisions

### Promotion failure visibility
- Post a PR comment when promotion fails — actionable for the human reviewer
- Include brief reason when known (e.g., "API error", "rate limit")
- Neutral attribution — no Booty branding in the comment
- If posting the comment fails (permissions, API error): fall back to logs only, no UI change

### "Linting clean" threshold
- Zero errors only — warnings do not block promotion
- If linter auto-fixes (e.g., ruff) and leaves zero errors: treat as clean
- Design for multiple linters — repos may use ruff, ESLint, golangci-lint, etc.; do not assume ruff-only
- All configured linters must pass — promotion requires zero errors from each

### Retry behavior on promotion failure
- Retry with backoff (e.g., 2–3 attempts total)
- Retry on 5xx, network errors; do not retry on 4xx (auth, not found, etc.)
- 2 retries (3 attempts total)
- After retries exhausted: still post the failure comment on the PR

### Self-modification signalling
- Add explicit note in PR body — current label + reviewer request are not enough
- Place note at top, within the Safety Summary section
- Explicit wording: "Draft by design: self-modification PRs are not auto-promoted"
- Self-mod PRs that fail tests still get the Test Failures section appended (same as regular PRs)

### Claude's Discretion
- Exact comment template wording
- Retry backoff timing and strategy
- Multi-linter configuration discovery and wiring (beyond ruff)
- GraphQL vs REST API approach for promotion

</decisions>

<specifics>
## Specific Ideas

- "We can't tell what the repo may need or use" — drove multi-linter design
- Neutral failure messaging — no Booty branding in promotion-failure comments
- Explicit self-mod rationale — reviewer should understand why it's draft by design

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-pr-promotion*
*Context gathered: 2026-02-15*
