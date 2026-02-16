# Phase 21: Permission Drift & Governor Integration - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

When Security detects changes in sensitive paths (workflows, infra, terraform, helm, k8s, iam, auth, security), it ESCALATEs (does not FAIL), persists a risk override, and the Governor consumes that override for deploy decisions. The PR is not blocked — only deploy risk is escalated. Scope is fixed from ROADMAP.md; discussion clarifies how to implement within this boundary.

</domain>

<decisions>
## Implementation Decisions

### Sensitive path "touched" definition
- Add, modify, delete, and rename — all count as touching
- Renames: path-based logic only (check both old and new paths); treat as add + delete for matching
- Binary changes: escalate — any change under a sensitive path counts
- Moves: escalate if either the old path or the new path is sensitive

### Check presentation on ESCALATE
- Conclusion: `success` — merge allowed; escalation is informational (does not block PR)
- Summary: list the specific paths that triggered escalation
- Title: vary by category (e.g. "Security escalated — workflow modified", "Security escalated — infra modified", "Security escalated — terraform modified" per path type)
- Annotations: none — summary only, no per-file annotations

### Override persistence & lookup
- Location: global — same state dir as Governor (`RELEASE_GOVERNOR_STATE_DIR` or `$HOME/.booty/state`)
- SHA matching: persist for every commit in the PR; Governor checks each commit in the diff for override (improves merge-commit coverage)
- Key structure: `(repo_full_name, sha)` — shared store, repo-scoped keys
- Payload: include paths — `{ risk_override, reason, paths: [...] }` for debugging/audit
- Known limitation: squash merges — squash commit is the only new commit; PR commits are not in the diff, so override lookup may miss. Governor's path-based risk may still catch it if paths overlap. Document as limitation.

### Override lifecycle & cleanup
- "Used" definition: after PR is merged (merge/squash commit lands on main)
- Cleanup: TTL 14 days + Governor prunes on read (removes override when consumed)
- File growth: must not grow unbounded — enforced by TTL + prune on read
- Race (Governor before Security): poll up to 2 minutes for override to appear, then proceed without override (use normal risk computation)

### Claude's Discretion
- Exact category-to-title mapping for path types (workflow, infra, terraform, helm, k8s, iam, auth, security)
- TTL implementation details (when/how to expire)
- Poll interval and backoff for Governor wait/retry

</decisions>

<specifics>
## Specific Ideas

- No specific requirements — open to standard approaches for path matching (PathSpec/gitwildmatch), storage format (JSON), and Governor integration (read before compute_risk_class).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-permission-drift-governor-integration*
*Context gathered: 2026-02-16*
