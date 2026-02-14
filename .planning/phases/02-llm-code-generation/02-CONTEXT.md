# Phase 2: LLM Code Generation - Context

**Gathered:** 2026-02-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Analyze GitHub issues and generate working code changes as pull requests. Takes an issue as input, produces a PR with conventional commits and structured description. Test execution and iterative refinement are Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Path restrictions
- Config-heavy restriction policy: block modifications to `.github/workflows/`, `.env`, secrets, CI configs, Dockerfiles, deployment manifests, and lockfiles
- Maintain an explicit allowlist/denylist of path patterns
- Reject changes that touch restricted paths rather than silently skipping them

### Prompt injection defense
- Sandboxed prompting: issue content is placed in a clearly-delimited untrusted zone in the LLM prompt
- Do not strip or sanitize issue content — preserve it fully but isolate it
- System prompt establishes boundaries; issue content is treated as user-provided data, not instructions

### Pre-commit validation
- Syntax check: verify generated code parses without errors
- Import check: verify imports resolve to real modules in the workspace
- Reject changes that fail either check before committing

### Size limits
- Both file count and token budget limits enforced
- File count cap: refuse issues that would require changing more files than the configured limit
- Token budget cap: bail out if the issue needs more context than fits in the LLM's window
- When limits are exceeded, comment on the issue explaining why the task is too large for automated handling

### Claude's Discretion
- Exact file count and token budget thresholds
- Denylist pattern syntax and defaults
- How validation errors are reported back to the LLM or user
- Issue analysis depth and code change strategy (not discussed — Claude has full flexibility)
- PR presentation style (not discussed — Claude has full flexibility)

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

*Phase: 02-llm-code-generation*
*Context gathered: 2026-02-14*
