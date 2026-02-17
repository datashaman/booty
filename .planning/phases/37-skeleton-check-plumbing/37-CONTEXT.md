# Phase 37: Skeleton + Check Plumbing - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Reviewer module skeleton, ReviewerConfig schema, check run lifecycle (queued → in_progress → success/failure), and single PR comment upsert with `<!-- booty-reviewer -->` marker. No LLM, no webhook wiring, no Review Engine — pure plumbing. Phase 38 adds events; Phase 39 adds review content.

</domain>

<decisions>
## Implementation Decisions

### Comment body when no review yet
- Create the comment only when Reviewer actually runs (never when disabled or non-agent PR)
- If Reviewer is queued/in_progress, upsert comment with short placeholder:
  - **Reviewer:** pending
  - Latest SHA: `<sha>` (actual commit SHA)
  - Status: queued | in_progress
- Do not create a comment when Reviewer is disabled or not applicable

### Unknown config key — user feedback
- Fail Reviewer only (do not affect Verifier, Security, or other agents)
- Check conclusion: failure with title "Reviewer config invalid"
- Also upsert the PR comment with the exact error and location:
  - Invalid .booty.yml reviewer config: unknown key 'enabeld' at line X
  - Fix the key or remove it
- Surface in both check output and PR comment — visible in GitHub, no log-only mode

### Check run title/summary text (queued/in_progress)
- Context name: `booty/reviewer`
- Queued: title "Booty Reviewer", summary "Queued for review…"
- In progress: title "Booty Reviewer", summary "Reviewing PR diff for engineering quality…"
- Titles stable across states; state-specific text in summary (mirror Verifier pattern)

### Comment marker format
- Use bounded block for safe idempotent updates:
  - `<!-- booty-reviewer -->`
  - body
  - `<!-- /booty-reviewer -->`
- Place block near the top of the comment, after a one-line heading, so updates don't disturb any appended content later

### Claude's Discretion
- Exact placeholder body layout (line breaks, formatting)
- Specific error message phrasing variants
- Module file structure within `src/booty/reviewer/`

</decisions>

<specifics>
## Specific Ideas

- Placeholder shows SHA and status (queued/in_progress) for operator visibility
- Comment marker block placement: after heading, near top — supports future appended content
- Mirror Verifier's check run pattern: stable title, state in summary

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 37-skeleton-check-plumbing*
*Context gathered: 2026-02-17*
