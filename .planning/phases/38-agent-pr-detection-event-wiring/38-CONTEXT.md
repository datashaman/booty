# Phase 38: Agent PR Detection + Event Wiring - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire Reviewer into the pull_request webhook. Reviewer runs only for agent PRs (opened, synchronize, reopened). Dedup and cancel behavior when new SHA arrives. Check titles: Queued/In progress "Booty Reviewer"; Success "Reviewer approved" or "Reviewer approved with suggestions"; Failure "Reviewer blocked". Phase 39 adds the Review Engine (LLM, rubric); this phase is event plumbing only.

</domain>

<decisions>
## Implementation Decisions

### Repo config check timing
- Enqueue on webhook for agent PRs when Reviewer globally enabled; worker loads `.booty.yml` and decides
- Webhook stays fast and uniform (no extra API call)
- Worker outcome:
  - Reviewer enabled in config → create `booty/reviewer` check, run review
  - Reviewer disabled or missing block → do nothing (no check, no comment)

### Cancel semantics
- Cooperative cancel (best-effort), no hard process kill
- On new SHA for same PR: mark prior run cancelled, enqueue new run
- In-flight worker checks a cancel flag between phases (before LLM call, before posting comment, before finalizing check) and exits early
- Conclusion: use `cancelled` or neutral per GitHub API support
- Mirror Verifier’s “cancel previous” intent but implementation is cooperative

### Dedup key
- Use `{repo_full_name}:{pr_number}:{head_sha}` for multi-repo safety
- Matches roadmap intent `(repo, pr_number, head_sha)`; avoids cross-repo collisions
- Verifier keeps its current `pr_number:head_sha` style; Reviewer uses repo-inclusive key

### Claude's Discretion
- Webhook early-return condition when Reviewer is the only enabled agent
- Exact cancel-flag check points in worker flow
- GitHub check conclusion when cancelled (cancelled vs completed/skipped)

</decisions>

<specifics>
## Specific Ideas

- Webhook latency matters — avoid fetching config at webhook time
- Worker no-op when disabled: silent, no check, no comment
- Cancel flag checked at phase boundaries to keep implementation simple

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 38-agent-pr-detection-event-wiring*
*Context gathered: 2026-02-17*
