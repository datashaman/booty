# Phase 27: Planner Foundation - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Plan schema (Pydantic), config (.booty.yml planner block), webhook for `agent:plan` label, and `booty plan` CLI skeleton. Foundation plumbing for Planner Agent — schema validates, webhook enqueues, CLI runs, artifacts store. Plan generation (LLM) and risk classification are Phase 29.

</domain>

<decisions>
## Implementation Decisions

### CLI output and behavior
- Silent by default; `--verbose` for progress/details
- `booty plan --text`: stdout by default, `--output <path>` to write to file
- On success: print path + one-line summary (goal snippet + step count)
- On failure: short error on stderr; `--verbose` for trace

### Webhook trigger and response
- Trigger on both `issues.opened` and `issues.labeled` when `agent:plan` present
- Respond 202 Accepted; planner runs async (enqueue job)
- When label added to existing issue: check for existing recent plan first — skip or update (idempotency detail in Phase 31)
- Unlabeled issues: no-op, 200 OK, log at debug

### Plan artifact naming and storage
- Issue-based: `plans/<owner>/<repo>/<issue>.json` (nested, multi-repo safe)
- Ad-hoc (`--text` without issue): `plans/ad-hoc-<timestamp>-<short_hash>.json`
- Auto-create plans directory like other Booty state dirs (release.json, memory.jsonl)
- Same location for CLI and webhook — no distinction by origin

### Schema scope for Phase 27
- **Required fields:** plan_version, goal, risk_level, touch_paths, steps, handoff_to_builder
- **Optional stubs:** assumptions, constraints, tests, rollback (empty list/default)
- **plan_version:** fixed `"1"` (validate equality)
- **Step shape:** id (P1..Pn), action enum (read|edit|add|run|verify), path/command nullable, acceptance required
- **handoff_to_builder:** all four required — branch_name_hint, commit_message_hint, pr_title, pr_body_outline

### Claude's Discretion
- Exact hash algorithm for ad-hoc filename (short_hash)
- Timestamp format for ad-hoc
- Verbose output wording/phrasing
- .booty.yml planner block keys beyond env overrides (if any)

</decisions>

<specifics>
## Specific Ideas

- "Follow existing pattern" for state dir creation — consistency with release.json, memory.jsonl
- "The origin is irrelevant; the artifact is what matters" — single storage layout for CLI and webhook
- Nested repo path "prevents collisions and scales cleanly to multi-repo control"
- Timestamp + hash for ad-hoc "avoids rare but painful collisions; deterministic enough"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 27-planner-foundation*
*Context gathered: 2026-02-16*
