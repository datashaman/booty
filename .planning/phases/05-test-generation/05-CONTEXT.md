# Phase 5: Test Generation - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Builder generates and validates unit tests for all code changes in every PR. Tests must pass before PR is finalized. This phase covers test generation only — PR promotion logic is Phase 6.

</domain>

<decisions>
## Implementation Decisions

### File placement & naming — Convention detection
- Builder must be **language-agnostic** — target repos can be Python, Go, Rust, PHP, C++, or any language
- **Combo detection approach:** structured code performs initial detection (language identification, existing test file discovery, config file parsing), then LLM receives those findings as context for informed test generation
- **Config files checked:** pyproject.toml, setup.cfg, tox.ini, Makefile, package.json, go.mod, Cargo.toml, etc. — language-appropriate config that reveals test runner and conventions
- **Existing test files:** scan for existing tests to infer framework, directory structure, and naming patterns
- No hardcoded defaults for any language — conventions are always derived from the repo itself

### Claude's Discretion
- Specific detection heuristics and priority ordering
- How to handle repos with mixed languages
- Fallback behavior when no conventions can be detected
- Test scope and coverage depth (what gets tested, edge cases vs happy path)
- LLM prompt strategy for test generation
- Test validation and retry logic when generated tests fail

</decisions>

<specifics>
## Specific Ideas

- "This project should use pytest, but other repos we cannot say for sure"
- Convention detection should happen once when a repo is first encountered, not on every PR
- The detection is a foundation that test generation builds on — get the conventions right first, then generate tests that fit

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-test-generation*
*Context gathered: 2026-02-15*
