# Phase 26: CLI - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `booty memory status` and `booty memory query` commands. Operators and developers inspect memory state and run lookups from the CLI. Scope: MEM-27, MEM-28. No new Memory capabilities — only CLI surface.

</domain>

<decisions>
## Implementation Decisions

### Status output
- **Layout:** Key/value lines, matching `booty governor status` style
- **Content:** enabled, record count, retention_days, state file path (for debugging). Omit max_matches to keep status terse
- **Disabled:** First line `Memory: disabled`; optional second line with reason when available (e.g. memory.enabled=false)
- **Not configured:** Treat same as disabled (no .booty.yml or missing memory block → disabled)

### Query input (PR vs SHA)
- **Repo:** Infer from workspace `git remote origin`; optional `--repo owner/repo` override (consistent with governor simulate)
- **Paths with --sha:** Use `git diff` of that commit by default; optional `--paths file1 file2 ...` to override
- **Workspace:** Support `--workspace`, default `.` (matches governor commands)
- **--pr:** Requires GITHUB_TOKEN to fetch PR diff; repo inferred or overridden
- **--sha:** Paths from git diff; repo inferred or overridden

### Query output
- **Human layout:** Bullet list, compact structure:
  - Line 1: `type  date  [severity]` (severity only when present)
  - Line 2: summary
  - Line 3: `Link: https://...`
  - Single blank line between matches
- **Fields:** type, date, severity (optional), summary, link — nothing else
- **Empty result:** Print `No related history found` (confirms query executed; avoids ambiguity in automation)
- **Match limit:** Add `--limit N`; defaults to config max_matches. Operators need deeper history occasionally
- **--json:** Machine-readable output (per MEM-28)

### Error & edge behavior
- **Memory disabled:** Exit 0, print `Memory: disabled`. Feature-disabled state, not runtime error. Consistent with ingest; avoids breaking scripts that probe capability
- **Invalid PR:** Exit 1, clear error. Example: `Error: PR 99999 not found in owner/repo`. Invalid input is operator error
- **Invalid SHA:** Exit 1, explicit error. Example: `Error: SHA abc123 not found in repository`. For PR mode, PR lookup failure already handles it
- **Missing GITHUB_TOKEN:** Exit 1, mode-specific messages:
  - `Error: GITHUB_TOKEN required for --pr (GitHub API lookup)`
  - `Error: GITHUB_TOKEN required to fetch commit metadata`
  Short, causal, actionable

### Claude's Discretion
- Exact key names in status (e.g. records vs record_count)
- JSON output structure for query
- Git diff command for --sha (sha^..sha or equivalent)
- When "fetch commit metadata" applies vs --pr

</decisions>

<specifics>
## Specific Ideas

- Status output matches governor status feel — key/value lines, terse
- Query human format: readable, fast to scan, avoids table wrapping in narrow terminals
- GITHUB_TOKEN messages: precision over mirroring governor wording
- Treat disabled/not-configured as capability probe, not failure — scripts may run `booty memory query` to check

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 26-cli*
*Context gathered: 2026-02-16*
