# Phase 3: Test-Driven Refinement - Context

**Gathered:** 2026-02-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Ensure generated code passes tests through iterative refinement with failure feedback. The system runs the target repo's test suite, feeds failures back to the LLM, and retries until tests pass or max attempts are exhausted. On permanent failure, it comments on the issue and opens a draft PR with partial work.

</domain>

<decisions>
## Implementation Decisions

### Test execution
- Test command is configured per-repo via a `.booty` config file (e.g., `.booty.yml`) in the target repo root
- Config file specifies: test command, timeout, and other repo-specific settings
- If no `.booty` config file exists in the target repo, the job fails — no unverified code gets submitted
- Test timeout is configurable in the `.booty` file with a sensible default (e.g., 5 minutes)

### Refinement loop
- Test output is truncated/filtered before feeding back to the LLM — extract relevant failure lines (tracebacks, assertion errors), trim the rest
- Targeted regeneration: LLM analyzes which files caused the failure and only regenerates those, preserving working code
- Last attempt only: each retry sees only the most recent code and its failure output, not cumulative history — keeps context lean
- Max retries is configurable in the `.booty` config file

### Claude's Discretion
- `.booty` config file format and schema details
- Test output parsing/filtering strategy
- How to determine which files are related to a failure
- Failure handling behavior (draft PR, issue comments, error formatting)
- Retry strategy for transient errors (API timeouts, rate limits) vs test failures
- Exponential backoff parameters

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-test-driven-refinement*
*Context gathered: 2026-02-14*
