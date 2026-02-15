# Project Research Summary

**Project:** Booty v1.1 - Test Generation & PR Promotion
**Domain:** LLM-powered test generation and automated PR workflow
**Researched:** 2026-02-15
**Confidence:** HIGH

## Executive Summary

Booty v1.1 adds test generation and PR promotion capabilities to the existing AI Builder pipeline. Research reveals this is a **capabilities expansion, not a stack expansion** — no new dependencies required. The existing magentic+Anthropic pipeline can generate test code using the same `@prompt` decorator pattern used for production code, and PyGithub already supports PR promotion via `mark_ready_for_review()` GraphQL mutation.

The recommended approach is to integrate test generation directly into the existing code generation phase (single LLM call producing both source and test files), then leverage the proven refinement loop for validation. PR promotion becomes a conditional final step: draft PRs are automatically promoted to ready-for-review when tests pass, except for self-modification PRs which always require manual review. This maintains the existing security posture while adding automation.

The critical risks center on test quality (generated tests that pass but don't actually validate behavior), non-deterministic test stability, and package hallucination. Mitigation requires test quality validation gates, deterministic prompt engineering, and dependency verification before execution. The existing refinement loop and token budget management need careful extension to handle test generation without breaking proven patterns.

## Key Findings

### Recommended Stack

**No new dependencies required.** All capabilities exist in the current stack:

**Core technologies:**
- **magentic[anthropic]** — Same `@prompt` decorator pattern used for code generation now generates test files. Test code is just Python code to the LLM.
- **PyGithub** — `PullRequest.mark_ready_for_review()` method supports draft-to-ready promotion via GraphQL mutation (available since v1.55, Booty uses v2.x)
- **Pydantic** — Existing `CodeGenerationPlan` and `FileChange` models already support test files without modification
- **structlog** — Existing logging infrastructure extends naturally to test generation and PR promotion events

**Integration points:**
- Test generation: Modify existing `generate_code_changes()` prompt to request tests alongside code
- Test refinement: Extend `regenerate_code_changes()` to fix source or tests based on failure analysis
- PR promotion: Add `promote_pr_to_ready()` function in `github/pulls.py`, call after PR creation if tests passed

**What NOT to add:**
- Test generation frameworks (pytest-evals, deepeval) — these test LLMs, not generate tests with LLMs
- GraphQL client libraries (gql, sgqlc) — PyGithub already wraps GitHub's GraphQL API
- Test AST manipulation (libcst, astroid) — LLM generates complete test files as text

### Expected Features

**Must have (table stakes):**
- Unit test generation for changed files — industry standard for automated testing tools
- Test execution before PR promotion — all PR automation validates tests before marking ready
- Test quality validation — LLM-generated tests need verification to avoid trivial/broken tests
- Feedback loop on test failure — LLM must fix broken tests it generates through refinement
- Test framework detection — must use project's existing test framework (pytest for Booty)
- Correct test file placement — tests go in `tests/` directory following pytest conventions

**Should have (competitive advantage):**
- Edge case identification — LLM identifies and tests boundary conditions automatically
- Test data generation — realistic test fixtures/data instead of placeholder values
- Smart test selection — integration tests only for files that interact with external systems
- Self-modification extra safety gates — Builder can modify itself, needs stronger promotion rules
- Auto-comment on promotion — explain why PR was promoted (which checks passed)

**Defer to v1.2+:**
- Coverage-driven test generation — generate tests to fill coverage gaps, not blanket coverage
- Test quality gates for promotion — don't promote if tests are trivial/low quality
- Mutation testing validation — verify tests catch bugs by introducing mutations (resource intensive)
- Rollback on post-promotion failure — demote back to draft if issues found after promotion

**Anti-features (deliberately avoid):**
- 100% coverage mandate — leads to trivial tests just to hit metrics
- Automated test deletion — dangerous, could delete important coverage
- Generating tests without execution — worthless without validation
- Auto-merge without human review — dangerous for self-modification

### Architecture Approach

Test generation integrates into the existing Builder pipeline at two points: (1) extending code generation to include test files, and (2) adding conditional PR promotion after PR creation. The key architectural insight is that test files are just more `FileChange` objects — no new data structures or processing steps needed. Tests flow through the existing workspace write → git commit → PR creation path.

**Modified pipeline flow:**
```
Analyze issue → Generate code AND TESTS (single LLM call) →
  → Run tests (existing + generated) →
  → If fail: refine code AND/OR tests →
  → Commit (source + tests) → Push →
  → Create PR (always draft) →
  → If tests passed AND not self-modification: promote to ready
```

**Major components:**
1. **Test generation prompt** — Extend existing `generate_code_changes()` prompt template to request test files alongside source files (same LLM call, not separate)
2. **Test refinement integration** — Extend `regenerate_code_changes()` to distinguish "test caught a bug" vs "test is incorrect" and fix accordingly
3. **PR promotion function** — New `promote_pr_to_ready()` in `github/pulls.py` using PyGithub's GraphQL mutation support
4. **Conditional promotion logic** — In `process_issue_to_pr()`, check `tests_passed AND not is_self_modification` before calling promotion

**Architectural patterns applied:**
- **Extend existing LLM call (not add new one)** — Generate tests in same prompt as code (simpler, shared context)
- **Leverage existing refinement loop** — Generated test failures trigger refinement just like source failures
- **Fail-safe promotion** — Non-critical operation shouldn't fail the job (log error, manual promotion still possible)
- **GraphQL via existing client** — PyGithub supports GraphQL, no new dependency needed

**Anti-patterns avoided:**
- Separate test validation phase (duplicates test execution)
- New LLM call for test generation (context split, coordination overhead)
- Synchronous PR promotion blocking job completion
- Test generation toggle (configuration complexity, partial features)

### Critical Pitfalls

1. **Test Quality Theater (Coverage Without Verification)** — LLM-generated tests achieve high coverage while providing false security. Tests check implementation details instead of behavior, always pass, miss edge cases. **Prevention:** Add mutation testing or require tests to fail against intentionally broken code; validate assertions exist; use quality gates before accepting tests.

2. **LLM Non-Determinism Breaking Test Stability** — Generated tests exhibit non-deterministic behavior (timing, random values, ordering), creating flaky tests that break CI/CD. **Prevention:** Explicitly instruct LLM to generate deterministic tests; track test success rates across multiple runs; quarantine flaky tests; run generated tests 3-5 times before committing.

3. **Package Hallucination in Generated Tests** — LLM hallucinates test dependencies (21.7% for open-source models, 5.2% for commercial). Tests import non-existent testing libraries or reference APIs that don't exist. **Prevention:** Validate all imports against installed packages before execution; include current library versions in prompts; parse imports and verify existence; track known hallucinations.

4. **Premature PR Promotion (False Positive Test Pass)** — Auto-promotion based solely on exit code 0 creates security bypass. Tests may pass despite being skipped, disabled, or having no assertions. **Prevention:** Multi-criteria promotion (test pass + coverage threshold + quality checks + security scans); never auto-promote self-modification; log all promotion criteria; human-in-loop flag for sensitive files.

5. **Test Generation Context Explosion** — Adding test generation doubles/triples context size, causing token budget overflows. Context includes: issue + repo files + generated code + test requirements + error messages from refinement. **Prevention:** Separate token budgets for code vs test generation; file-by-file test generation; prune context during refinement (only failures, not full output); fail fast if budget < 30% remaining.

## Cross-Cutting Themes

### 1. Simplicity Through Reuse
The strongest theme across all research: every capability needed already exists in the Booty stack. Test generation uses the same prompt pattern as code generation. PR promotion uses the same GitHub client. Test refinement uses the same loop. The implementation challenge is integration, not new technology.

### 2. Quality Over Automation
A consistent warning across test generation research: automated test generation can create false confidence. The system must validate that generated tests are meaningful, not just syntactically correct. This requires explicit quality gates beyond "tests pass."

### 3. One-Shot Generation, Code-Only Refinement
The existing refinement loop (`refine_until_tests_pass`) is proven to work for code generation. The critical architectural decision is to NOT break this by regenerating tests in each refinement iteration. Generate tests once with code, then freeze tests and refine only code. This avoids circular dependencies and infinite loops.

### 4. Fail-Safe Automation
PR promotion is a non-critical operation that shouldn't fail the entire job. If promotion fails (network error, permissions, API issue), the PR still exists as a draft and can be manually promoted. This graceful degradation pattern should extend throughout the implementation.

### 5. Self-Modification Requires Eternal Vigilance
The existing safety mechanism for self-modification PRs (always require manual review) must be preserved. Test generation and PR promotion add new attack surfaces (malicious tests, bypassed gates) that could subvert this safety if not carefully guarded.

## MVP Scope Recommendation

Based on research findings, recommended phase breakdown:

### Phase 1: Test Generation Architecture
**Duration:** 3 days
**Rationale:** Test generation is foundational — must be working before PR promotion can be meaningful. This phase establishes quality gates and validation patterns that prevent downstream issues.

**Delivers:**
- Modified `generate_code_changes()` prompt requesting test files alongside source
- Test quality validation (assertion detection, edge case heuristics)
- Dependency verification (detect hallucinated packages before execution)
- Integration with existing token budget management
- File-by-file test generation to manage context size

**Addresses features:**
- Unit test generation for changed files (must-have)
- Test framework detection (must-have)
- Correct test file placement (must-have)
- Edge case identification (should-have)

**Avoids pitfalls:**
- Test Quality Theater — validation gates prevent trivial tests
- Package Hallucination — dependency verification before execution
- Test Generation Context Explosion — token budget management from start

**Research flag:** SKIP — well-documented prompt engineering, existing patterns clear

### Phase 2: Test Execution Integration
**Duration:** 2 days
**Rationale:** Extends existing refinement loop to handle generated tests. Critical to preserve working behavior (test-driven refinement) while adding new capability.

**Delivers:**
- Modified `regenerate_code_changes()` prompt to fix source OR tests based on failure
- Flaky test detection (run tests 3-5 times before accepting)
- Quality checks extended to test files (ruff validation)
- One-shot generation pattern (tests frozen after initial generation)
- Test vs source code separation in logging and PR body

**Addresses features:**
- Test execution before PR promotion (must-have)
- Feedback loop on test failure (must-have)
- Test quality validation (must-have)

**Avoids pitfalls:**
- LLM Non-Determinism — flaky test detection and retry logic
- Test Generation Breaking Refinement Loop — one-shot pattern preserves existing behavior
- Quality Check Ordering Chaos — extend validation to test files

**Research flag:** SKIP — existing refinement loop well-understood, extension pattern clear

### Phase 3: PR Promotion Logic
**Duration:** 2 days
**Rationale:** Automated promotion is the user-facing feature. Depends on reliable test generation and execution from Phases 1-2. Implements safety gates to prevent premature promotion.

**Delivers:**
- `promote_pr_to_ready()` function using PyGithub GraphQL API
- Multi-criteria promotion (tests passed + not self-modification)
- Promotion audit logging (which checks validated)
- PR body updates (test generation summary, promotion status)
- Graceful promotion failure handling (log error, don't fail job)

**Addresses features:**
- Create PR as draft initially (must-have)
- Promote to ready when tests pass (must-have)
- Self-modification extra safety gates (should-have)
- Auto-comment on promotion (should-have)

**Avoids pitfalls:**
- Premature PR Promotion — multi-criteria validation, audit logging
- Draft PR Mental Model Confusion — clear status communication in PR body
- PR Description Pollution — aggregate test changes, collapsible sections

**Research flag:** SKIP — PyGithub API verified, promotion logic straightforward

### Phase Ordering Rationale

**Why Phase 1 first:** Test generation must work reliably before PR promotion becomes meaningful. Quality gates established here prevent "garbage in, garbage out" problems downstream. Token budget management and dependency validation are prerequisites for safe execution.

**Why Phase 2 before Phase 3:** PR promotion depends on reliable test execution results. The refinement loop integration must preserve existing stability (critical to project success) before adding automation. Flaky test detection in Phase 2 ensures Phase 3 promotion decisions are based on deterministic results.

**Why this grouping:** Each phase builds on the previous while delivering independent value. Phase 1 can ship as "test generation without promotion" (still valuable). Phase 2 improves test reliability. Phase 3 adds convenience automation. This allows incremental validation and rollback if needed.

**How this avoids pitfalls:**
- Early quality gates (Phase 1) prevent test quality theater
- One-shot generation pattern (Phase 2) avoids refinement loop chaos
- Multi-criteria promotion (Phase 3) prevents false positive auto-promotion
- Token budget management (Phase 1) prevents context explosion
- Flaky test detection (Phase 2) ensures stable promotion decisions (Phase 3)

### Research Flags

**All phases: SKIP deeper research** — well-documented patterns, existing architecture clear

- **Phase 1:** Prompt engineering and LLM integration follow established magentic patterns. Dependency verification is straightforward PyPI/package registry lookup.
- **Phase 2:** Refinement loop extension reuses existing architecture. Flaky test detection is standard practice (retry N times, check consistency).
- **Phase 3:** PyGithub GraphQL API usage verified via documentation and GitHub API docs. Promotion logic is conditional branching (no complex patterns).

**No phases require `/gsd:research-phase`** — this is a subsequent milestone extending proven architecture, not greenfield development.

## Critical Decisions

### Decision 1: Single LLM Call vs Separate Test Generation
**Choice:** Single LLM call generating both source and tests
**Rationale:** Shared context ensures tests match implementation. Simpler architecture (no coordination). Lower token cost (no context duplication). Matches existing pattern (all file changes in one `CodeGenerationPlan`).
**Trade-off:** Less flexibility to regenerate tests independently, but research shows one-shot test generation is superior pattern.

### Decision 2: One-Shot vs Iterative Test Regeneration
**Choice:** Generate tests once, refine only code in subsequent iterations
**Rationale:** Preserves existing refinement loop stability. Avoids circular dependency (tests testing tests). Tests become stable validation anchor. Prevents token budget explosion from repeated test generation.
**Trade-off:** Tests may not adapt if code structure changes fundamentally, but research shows this is rare and acceptable.

### Decision 3: Multi-Criteria vs Tests-Only Promotion
**Choice:** Require tests passed AND not self-modification (future: + coverage + quality checks)
**Rationale:** Tests passing alone insufficient for safety. Self-modification must never auto-promote (security). Multi-criteria leaves room for future quality gates without architecture changes.
**Trade-off:** More conservative (some valid PRs remain draft), but safety outweighs convenience.

### Decision 4: GraphQL via PyGithub vs Dedicated GraphQL Client
**Choice:** Use PyGithub's GraphQL mutation support
**Rationale:** Zero new dependencies. Same authentication and error handling. PyGithub abstracts GitHub API complexity. Sufficient for single mutation (`mark_ready_for_review`).
**Trade-off:** Less control over GraphQL specifics, but unnecessary for this use case.

### Decision 5: Test Files in Same Commit vs Separate Commits
**Choice:** Single commit containing source changes + generated tests
**Rationale:** Atomic change (tests validate the code they accompany). Simpler git history. Matches existing pattern (all `FileChange` objects committed together).
**Trade-off:** Larger commits, but tests are inherently coupled to implementation.

## Risk Summary

### High Risk (actively mitigate in implementation)

| Risk | Impact | Mitigation |
|------|--------|------------|
| Test Quality Theater | **CRITICAL** — false confidence undermines entire feature | Test quality validation gates; mutation testing consideration; assertion density checks; require edge cases |
| Premature PR Promotion | **HIGH** — security bypass, bad code merged | Multi-criteria promotion; preserve self-modification manual review; audit logging; human-in-loop for sensitive files |
| Refinement Loop Breakage | **HIGH** — breaks existing proven functionality | One-shot test generation; extensive testing of refinement scenarios; preserve existing behavior |
| Package Hallucination | **HIGH** — tests fail to execute, blocking pipeline | Dependency verification before execution; track hallucinations; explicit library versions in prompts |

### Medium Risk (monitor and log)

| Risk | Impact | Mitigation |
|------|--------|------------|
| Test Stability (Flakiness) | **MEDIUM** — unreliable promotion decisions | Run tests 3-5 times; deterministic prompt engineering; quarantine flaky tests |
| Token Budget Overflow | **MEDIUM** — incomplete test generation | Separate budgets; file-by-file generation; context pruning in refinement; early warning |
| Integration Test Dependencies | **MEDIUM** — tests fail due to environment | Constrain to available resources; define test environment in .booty.yml; skip unavailable integrations |

### Low Risk (acceptable, document)

| Risk | Impact | Mitigation |
|------|--------|------------|
| Promotion API Failure | **LOW** — PR remains draft (manual promotion works) | Graceful degradation; log error; don't fail job |
| PR Description Verbosity | **LOW** — harder to read, cosmetic | Aggregate test changes; collapsible sections; link to diffs |
| Test File Naming Collisions | **LOW** — prevented by LLM understanding conventions | Extract patterns from existing tests; validate before writing |

### Risk Mitigation Strategy

**Phase 1 addresses:** Test quality theater, package hallucination, token budget overflow
**Phase 2 addresses:** Test stability, refinement loop breakage, integration test dependencies
**Phase 3 addresses:** Premature PR promotion, promotion API failure, PR description verbosity

This sequencing ensures highest-risk issues tackled early, with later phases building on validated foundations.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | Direct codebase analysis confirms all capabilities present; PyGithub API verified via documentation and community sources |
| Features | **HIGH** | Table stakes validated across multiple automated testing resources; differentiators derived from competitive analysis |
| Architecture | **HIGH** | Existing Booty pipeline well-documented; integration points identified through code reading; patterns proven in current implementation |
| Pitfalls | **MEDIUM** | Critical pitfalls validated across multiple sources; integration pitfalls derived from architecture analysis; some edge cases inferred |

**Overall confidence:** HIGH

Research is comprehensive across all areas. Stack requirements conclusively verified (no new dependencies). Architecture integration points identified through direct code analysis. Feature expectations validated against industry standards. Pitfalls researched extensively with multiple corroborating sources.

The MEDIUM confidence on pitfalls reflects that some integration challenges (refinement loop interactions, token budget management) are predictive based on architectural analysis rather than directly observed. However, these are well-reasoned predictions grounded in existing system behavior.

### Gaps to Address

**Test quality metrics:** Research identified test quality validation as critical but didn't specify exact heuristics. Implementation should define:
- Minimum assertions per test
- Edge case detection patterns
- When to reject generated tests as "too trivial"
- Whether to implement mutation testing (high value, high cost)

**Token budget allocation:** Existing TokenBudget class manages code generation. Research recommends separate budgets for test generation but didn't quantify optimal split. Implementation should determine:
- What percentage of total budget for tests vs code
- File-by-file vs all-at-once generation (research suggests file-by-file)
- How to handle budget exhaustion mid-generation

**Integration test scope:** Research noted integration tests require external services unavailable in isolated workspace. Implementation must define:
- Which integrations are "safe" (filesystem, subprocess) vs "unsafe" (database, API)
- How to detect when generated tests require unsafe dependencies
- Whether to skip or fail when unsafe integration tests generated

**PR promotion criteria:** Research established multi-criteria promotion as best practice but didn't specify all criteria. Current implementation: tests passed + not self-modification. Future enhancements:
- Minimum coverage threshold (what percentage?)
- Quality check pass required? (ruff, mypy)
- Security scan results (dependency vulnerabilities)

These gaps are addressable during implementation through testing and iteration. None are blockers — reasonable defaults exist for all.

## Sources

### Primary (HIGH confidence)

**Codebase analysis:**
- Existing Booty codebase (`src/booty/code_gen/generator.py`, `src/booty/llm/prompts.py`, `src/booty/github/pulls.py`, `src/booty/test_runner/executor.py`)
- `pyproject.toml` dependency declarations
- Existing LLM prompt patterns and Pydantic models

**GitHub API verification:**
- [PyGithub PullRequest documentation](https://pygithub.readthedocs.io/en/stable/github_objects/PullRequest.html)
- [GitHub GraphQL API - Mutations](https://docs.github.com/en/graphql/reference/mutations)
- [gh pr ready CLI documentation](https://cli.github.com/manual/gh_pr_ready)
- [PyGithub Issue #2989](https://github.com/PyGithub/PyGithub/issues/2989) — mark_ready_for_review capability confirmation

### Secondary (MEDIUM confidence)

**Test generation research:**
- [LLM-Powered Test Case Generation](https://www.frugaltesting.com/blog/llm-powered-test-case-generation-enhancing-coverage-and-efficiency)
- [Mastering Test Automation with LLMs](https://www.frugaltesting.com/blog/mastering-test-automation-with-llms-a-step-by-step-approach)
- [Choosing LLMs for Unit Test Generation](https://research.redhat.com/blog/2025/04/21/choosing-llms-to-generate-high-quality-unit-tests-for-code/)
- [GitHub TestPilot](https://github.com/githubnext/testpilot) — LLM test generation reference implementation
- [Automating TDD with LLMs](https://medium.com/@benjamin22-314/automating-test-driven-development-with-llms-c05e7a3cdfe1)

**Pitfalls and anti-patterns:**
- [Package Hallucinations Security Risk](https://www.darkreading.com/application-security/ai-code-tools-widely-hallucinate-packages) — 21.7% hallucination rate for open-source models
- [Test Coverage False Security](https://wearecommunity.io/communities/testautomation/articles/6307)
- [LLM Determinism Challenges](https://unstract.com/blog/understanding-why-deterministic-output-from-llms-is-nearly-impossible/)
- [Flaky Tests in CI/CD](https://www.ranorex.com/blog/flaky-tests/)
- [GitHub Reviewers Bypass Vulnerability](https://www.legitsecurity.com/blog/bypassing-github-required-reviewers-to-submit-malicious-code)

**PR automation research:**
- [GitHub PR Stage Documentation](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/changing-the-stage-of-a-pull-request)
- [Streamlining Pull Request Process](https://graphite.dev/guides/streamlining-pull-request-process-automation)
- [Pull Request Testing QA Process](https://testquality.com/pull-request-testing-qa-pr-processes/)

### Tertiary (contextual understanding)

**Unit vs integration testing:**
- [Unit Testing vs Integration Testing](https://circleci.com/blog/unit-testing-vs-integration-testing/)
- [AI's Role in Testing](https://www.qodo.ai/blog/unit-testing-vs-integration-testing-ais-role-in-redefining-software-quality/)

**Test automation best practices:**
- [Test Automation Anti-Patterns](https://www.testdevlab.com/blog/5-test-automation-anti-patterns-and-how-to-avoid-them)
- [Software Testing Anti-Patterns](https://blog.codepipes.com/testing/software-testing-antipatterns.html)
- [Quality Over Quantity in Testing](https://dzone.com/articles/why-to-choose-quality-over-quantity-in-software-te)

---

**Research completed:** 2026-02-15
**Ready for roadmap:** Yes

**Next step:** Roadmap creation can proceed with confidence. All implementation decisions grounded in research. No additional research phases needed during planning.
