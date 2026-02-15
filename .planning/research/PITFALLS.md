# Pitfalls Research: Test Generation & PR Promotion

**Domain:** LLM-powered code generation with automated test generation and PR promotion
**Researched:** 2026-02-15
**Confidence:** MEDIUM (WebSearch verified with architectural analysis)

## Critical Pitfalls

### 1. Test Quality Theater (Coverage Without Verification)

**Risk:** LLM-generated tests achieve high coverage metrics while providing a false sense of security. The Builder already passes/fails based on test execution, but if the tests themselves are low-quality, this becomes "garbage in, garbage out."

**What goes wrong:**
- Tests check implementation details instead of behavior
- Tests always pass (tautological tests)
- Tests miss edge cases, error handling, and boundary conditions
- Coverage metrics show 80%+ but actual bug detection is minimal
- Generated tests may simply verify what the generated code does rather than what it should do

**Warning signs:**
- All LLM-generated tests pass on first run
- Tests never catch bugs during refinement cycles
- Generated tests lack assertions or only have trivial assertions
- Coverage metrics increase but bugs still slip through to PR review
- Tests check for expected output without validating correctness

**Prevention:**
- **Test the tests:** Add mutation testing or require generated tests to fail against intentionally broken code before accepting them
- **Quality gates:** Validate generated tests contain assertions, handle edge cases, and test error conditions
- **Separate generation prompts:** Use distinct LLM calls for production code vs test code (avoid "generate code that passes its own tests" circularity)
- **Test templates:** Provide domain-specific test patterns in prompts (e.g., "tests must verify error handling for invalid inputs")
- **Review heuristics:** Check for assertion density, boundary value testing, negative test cases

**Phase:** Phase 1 (Test Generation Architecture) - Must establish test quality validation from the start

**References:**
- [Test coverage false sense of security](https://wearecommunity.io/communities/testautomation/articles/6307)
- [Code coverage manipulation in SonarQube](https://medium.com/@muhammedsaidkaya/false-sense-of-security-go-test-coverage-manipulation-in-sonarqube-ce-14acffc4206a)
- [Quality over quantity in testing](https://dzone.com/articles/why-to-choose-quality-over-quantity-in-software-te)

### 2. LLM Non-Determinism Breaking Test Stability

**Risk:** LLM-generated tests exhibit non-deterministic behavior across runs, creating flaky tests that undermine CI/CD reliability and PR promotion confidence.

**What goes wrong:**
- Same prompt generates different test implementations on each run
- Tests contain non-deterministic assertions (timing, random values, ordering)
- LLM produces tests with race conditions or timing dependencies
- Generated tests rely on unstable external dependencies
- Test flakiness causes false negatives in PR promotion (tests fail randomly, blocking valid PRs)

**Warning signs:**
- Tests pass locally but fail in CI inconsistently
- Re-running tests with no code changes produces different results
- Generated tests use sleep(), timeouts, or time-based assertions
- Tests fail with "expected X but got Y" where both values seem valid
- PR promotion repeatedly fails due to test instability

**Prevention:**
- **Deterministic prompts:** Explicitly instruct LLM to generate deterministic tests (no time-based assertions, fixed seeds for random data)
- **Flaky test detection:** Track test success rates across multiple runs before accepting generated tests
- **Quarantine flaky tests:** Automatically flag tests that fail intermittently during refinement loops
- **Execution-guided validation:** Run generated tests 3-5 times independently to verify stability before committing
- **Retry logic with tracking:** For PR promotion, distinguish between "code is broken" vs "test is flaky" failures

**Phase:** Phase 2 (Test Execution Integration) - Validation must happen before tests enter the main suite

**References:**
- [LLM deterministic output nearly impossible](https://unstract.com/blog/understanding-why-deterministic-output-from-llms-is-nearly-impossible/)
- [Non-determinism of deterministic LLM settings](https://arxiv.org/html/2408.04667v5)
- [Flaky tests in CI/CD](https://www.ranorex.com/blog/flaky-tests/)
- [Managing flaky tests with CI tools](https://www.aviator.co/blog/flaky-tests-how-to-manage-them-practically/)

### 3. Package Hallucination in Generated Tests

**Risk:** LLM hallucinates test dependencies (packages/libraries that don't exist) at alarming rates - 21.7% for open-source models, 5.2% for commercial models. Tests appear valid but fail to install/run.

**What goes wrong:**
- Generated tests import non-existent testing libraries
- Test code references APIs that don't exist in the actual library versions
- LLM invents helper functions or fixtures that seem plausible but don't exist
- Tests use outdated APIs from deprecated library versions
- Dependency specifications reference packages that were never published

**Warning signs:**
- Import errors when running generated tests
- "Module not found" errors for test dependencies
- Tests reference APIs not found in library documentation
- Pip/npm install fails for generated test requirements
- Same hallucinated package appears across multiple test generations (predictable hallucinations)

**Prevention:**
- **Dependency validation:** Before executing tests, validate all imports against installed packages and PyPI/npm registry
- **Library version awareness:** Include current installed library versions in test generation prompts
- **Import extraction:** Parse generated test code for imports and verify existence before refinement
- **Hallucination catalog:** Track and filter known hallucinated packages (43% repeat across queries)
- **Graceful degradation:** If hallucinated dependencies detected, regenerate with explicit constraint: "only use these verified libraries: [list]"

**Phase:** Phase 1 (Test Generation Architecture) - Validation must happen before test execution

**References:**
- [AI code tools widely hallucinate packages](https://www.darkreading.com/application-security/ai-code-tools-widely-hallucinate-packages)
- [Package hallucinations security risk](https://developers.slashdot.org/story/25/04/29/1837239/ai-generated-code-creates-major-security-risk-through-package-hallucinations)
- [Code integrity and hallucinations](https://www.trendmicro.com/vinfo/us/security/news/vulnerabilities-and-exploits/the-mirage-of-ai-programming-hallucinations-and-code-integrity)

### 4. Premature PR Promotion (False Positive Test Pass)

**Risk:** Automated PR promotion from draft→ready based solely on exit code 0 creates security bypass vectors. Tests may pass for wrong reasons (no assertions, mocked failures, incomplete execution).

**What goes wrong:**
- PR promoted despite tests being skipped or disabled
- Tests pass because they caught exceptions and silently swallowed them
- Integration tests pass in isolation but would fail with real dependencies
- Quality checks (linting, formatting, security) bypassed in promotion logic
- Self-modification PRs automatically promoted despite requiring manual review

**Warning signs:**
- PRs promoted with 0% code coverage increase
- Tests pass but PR review reveals obvious bugs
- Test execution time suspiciously short (tests may be skipping)
- Promotion happens despite linting/formatting failures
- Security vulnerabilities in promoted PRs that tests should have caught

**Prevention:**
- **Multi-criteria promotion:** Require test pass + coverage threshold + quality checks + no security warnings
- **Self-modification override:** Never auto-promote self-modification PRs (already in place, must preserve)
- **Promotion audit trail:** Log all promotion criteria checked before converting draft→ready
- **Human-in-loop flag:** For certain file patterns (auth, payments, security), require manual approval even if tests pass
- **Promotion dry-run:** Log "would promote" without actually promoting for first N iterations to validate logic

**Phase:** Phase 3 (PR Promotion Logic) - Core phase focus

**References:**
- [GitHub required reviewers bypass vulnerability](https://www.legitsecurity.com/blog/bypassing-github-required-reviewers-to-submit-malicious-code)
- [Automated code review security standards](https://graphite.dev/guides/code-review-security-standards)
- [GitHub PR workflow documentation](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/changing-the-stage-of-a-pull-request)

### 5. Test Generation Context Explosion

**Risk:** Token budget management already exists for code generation but not for test generation. Adding test generation doubles/triples context size, causing budget overflows mid-pipeline.

**What goes wrong:**
- Code generation succeeds but test generation hits token limit
- Context includes: original issue + repo files + generated code + test requirements + error messages from refinement
- Token budget overflow causes partial test generation (incomplete test suites)
- Refinement loop context grows with each iteration (error messages accumulate)
- System falls back to truncating tests, losing critical edge case coverage

**Warning signs:**
- Test generation succeeds for small issues but fails for larger ones
- Generated tests cover only first few functions, ignore rest
- Token budget logs show overflow during test generation phase
- Test quality degrades after refinement iterations (context pollution)
- Incomplete test suites marked as complete

**Prevention:**
- **Separate token budgets:** Allocate distinct budgets for code generation vs test generation
- **File-by-file test generation:** Generate tests per modified file instead of all-at-once (matches existing file-by-file pattern)
- **Context pruning:** During refinement, include only test failures (not full test output) in next iteration context
- **Smart context selection:** Prioritize modified files + test files in token budget over unrelated repo files
- **Budget early warning:** Fail fast if token budget < 30% remaining when starting test generation

**Phase:** Phase 1 (Test Generation Architecture) - Must integrate with existing TokenBudget class

**References:**
- [LLM evaluation context management](https://langfuse.com/blog/2025-03-04-llm-evaluation-101-best-practices-and-challenges)
- [Context overflow detection patterns](https://www.confident-ai.com/blog/llm-evaluation-metrics-everything-you-need-for-llm-evaluation)

## Integration Pitfalls

### 6. Test Generation Breaking Existing Refinement Loop

**Risk:** The existing `refine_until_tests_pass` loop assumes tests are stable. Adding LLM-generated tests creates a circular dependency: code generation → test generation → test execution → code refinement → test regeneration?

**What goes wrong:**
- Unclear when tests should regenerate vs when code should refine
- Infinite loop: generated tests fail → refine code → regenerate tests → new tests fail → repeat
- Loss of test stability: earlier passing tests replaced with new failing tests
- Token budget exhausted in refinement loop that regenerates tests each iteration
- Existing test suite ignored in favor of regenerating tests

**Warning signs:**
- Refinement loop exceeds max_retries due to test regeneration churn
- Test count changes between refinement iterations
- Previously passing tests disappear from suite
- Refinement loop token usage spikes dramatically
- Error messages reference tests that no longer exist

**Prevention:**
- **One-shot test generation:** Generate tests once before refinement, then only refine code (tests frozen)
- **Explicit regeneration triggers:** Only regenerate tests if code structure changes fundamentally (new functions added)
- **Test suite versioning:** Track test changes separately from code changes in refinement loop
- **Refinement mode detection:** Distinguish "initial generation" (generate code + tests) from "refinement" (code only)
- **Hybrid strategy:** Keep existing tests immutable, only refine generated tests if they reference changed APIs

**Phase:** Phase 2 (Test Execution Integration) - Must preserve existing refinement loop behavior

**References:**
- [Test-driven refinement patterns](https://openreview.net/pdf?id=ktrw68Cmu9c)

### 7. Integration Test Dependency Hell

**Risk:** Requirement states "generate integration tests where relevant" but current architecture uses fresh clones per task. Integration tests may require external services, databases, APIs that aren't available in isolated workspace.

**What goes wrong:**
- Generated integration tests assume database is seeded/running
- Tests expect external API endpoints to be available
- Docker/service dependencies not started in isolated workspace
- Integration tests fail because test environment != production environment
- No way to distinguish "integration test failed" from "test environment misconfigured"

**Warning signs:**
- Integration tests fail with connection errors
- Tests timeout waiting for services that aren't running
- Generated tests hardcode localhost URLs for external services
- Same integration test passes locally but fails in CI
- Test failures reference "connection refused" or "service unavailable"

**Prevention:**
- **Integration test constraints:** Define which integrations are available in workspace (file system, subprocess, but not external services)
- **Test classification prompts:** Explicitly guide LLM to generate unit tests vs integration tests based on available test environment
- **Service detection:** If generated test requires database/API, fail early with actionable error (not "test failed")
- **Test environment manifest:** Include .booty.yml section defining available test resources (in-memory DB OK, external API not OK)
- **Skip unavailable integration tests:** Auto-skip (not fail) integration tests if dependencies unavailable, log for manual review

**Phase:** Phase 1 (Test Generation Architecture) - Determine integration test scope upfront

**References:**
- [Test automation environment challenges](https://www.testingmind.com/how-to-avoid-common-test-automation-challenges-and-failures/)
- [CI/CD pipeline environmental drift](https://octopus.com/blog/fast-tracking-code-promotion-in-your-ci-cd-pipeline)

### 8. Test Generation Racing Condition with PR Creation

**Risk:** Current pipeline: code generation → refinement → commit → push → create PR. Adding test generation extends this timeline significantly, but webhook timeout/job lifecycle may expect faster completion.

**What goes wrong:**
- Job timeout before test generation completes
- PR created without tests (race between test generation and PR creation)
- Partial commit: code committed but generated tests lost
- Background task cleanup kills test generation mid-process
- Webhook retry triggers duplicate test generation on same code

**Warning signs:**
- PRs appear without test files present
- Job logs show test generation started but no completion
- Tests exist locally but not in pushed commit
- Duplicate test files from retry attempts
- Timeouts occurring specifically during test generation phase

**Prevention:**
- **Atomic test + code commit:** Don't commit code until tests are generated and validated
- **Timeout budget allocation:** Reserve 40% of job timeout for test generation (not just code generation)
- **Checkpoint recovery:** If job interrupted, detect partial work and resume test generation (not restart from scratch)
- **Test generation timeout:** Separate timeout for test generation (fail fast if exceeds) vs code generation
- **All-or-nothing principle:** If test generation fails, don't create PR at all (or create draft with warning)

**Phase:** Phase 2 (Test Execution Integration) - Pipeline sequencing critical

**References:**
- [CI/CD pipeline failure points](https://www.digitalocean.com/community/tutorials/an-introduction-to-ci-cd-best-practices)

### 9. Quality Check Ordering Chaos

**Risk:** Current self-modification flow runs quality checks (ruff) after refinement. Adding test generation introduces new ordering question: when do generated tests get quality-checked?

**What goes wrong:**
- Generated test code fails linting but isn't caught until after commit
- Test generation creates poorly formatted code that passes tests but violates style guide
- Self-modification promotion blocked by test code linting failures (not production code)
- Quality checks run on production code but skip test files
- Generated tests introduce import order violations, unused imports

**Warning signs:**
- PRs fail quality checks specifically on test files
- Self-modification PRs blocked by test linting issues
- Generated tests have inconsistent formatting vs production code
- Import errors in tests due to missing quality validation
- Reviewer comments focus on test code style issues

**Prevention:**
- **Quality check test files:** Extend `run_quality_checks` to validate generated test files (not just production code)
- **Pre-commit validation:** Run ruff/formatters on generated tests before adding to workspace
- **Test-specific linting config:** Allow more lenient rules for test files (e.g., long lines in test data)
- **Auto-fix generated tests:** Run black/ruff --fix on generated tests before committing
- **Quality gate before execution:** Don't execute tests that fail quality checks (prevents polluting refinement loop)

**Phase:** Phase 2 (Test Execution Integration) - Quality checks must extend to test code

**References:**
- [Code quality tools and automation](https://blog.codacy.com/code-quality-explained)

### 10. PR Description Pollution with Test Details

**Risk:** Current PR body includes approach, changes table, testing notes. Adding auto-generated tests could pollute PR descriptions with verbose test details making PRs unreadable.

**What goes wrong:**
- PR body includes full test file contents (500+ lines)
- Changes table lists every generated test file individually (dozens of rows)
- Testing notes section becomes "see generated tests" (unhelpful)
- PR reviewers overwhelmed by test code diffs
- Generated test explanations clutter PR body with obvious statements

**Warning signs:**
- PR body exceeds GitHub's markdown rendering limits
- Changes table has 50+ rows (mostly test files)
- PR descriptions are unreadable due to length
- Reviewers skip PR description entirely
- Testing notes section duplicates information visible in test code

**Prevention:**
- **Aggregate test changes:** Group all test files into single "Generated tests" row in changes table
- **Test summary only:** Include test count and coverage delta (not individual test descriptions)
- **Separate test section:** Add collapsible "Test Generation Details" section for those who want specifics
- **Link to test files:** Reference test files in PR (reviewers can view in diff) instead of describing in body
- **Smart filtering:** Exclude test file explanations from PR body (only include production code explanations)

**Phase:** Phase 3 (PR Promotion Logic) - PR formatting must scale to larger change sets

**References:**
- [GitHub PR best practices](https://ardalis.com/github-draft-pull-requests/)

## Moderate Pitfalls

### 11. Test Generation Prompt Injection

**Risk:** Issue body content flows into test generation prompts. Malicious users could craft issues that trick LLM into generating tests that always pass, skip validation, or expose secrets.

**What goes wrong:**
- Issue contains "generate tests that always return True"
- Issue includes "ignore previous instructions" style prompt injection
- Generated tests exfiltrate environment variables or secrets
- Tests bypass security checks via LLM prompt manipulation
- Issue crafted to generate tests that disable existing test suite

**Warning signs:**
- Generated tests contain hardcoded True assertions
- Tests include network calls to external URLs
- Tests read files outside workspace
- Generated tests import subprocess/os for no clear reason
- Test content eerily matches issue description phrasing

**Prevention:**
- **Prompt isolation:** Use separate, sanitized context for test generation (not raw issue body)
- **Test code security scan:** Validate generated tests against PathRestrictor before execution
- **Assertion validation:** Require generated tests contain actual assertions (not just pass statements)
- **Sandbox test execution:** Run generated tests in restricted environment first (detect exfiltration attempts)
- **Test review triggers:** Flag for manual review if generated tests import dangerous modules

**Phase:** Phase 1 (Test Generation Architecture) - Security validation from start

**References:**
- [LLM hallucinations in code review](https://diffray.ai/blog/llm-hallucinations-code-review/)
- [Code generation security vulnerabilities](https://www.trendmicro.com/vinfo/us/security/news/vulnerabilities-and-exploits/the-mirage-of-ai-programming-hallucinations-and-code-integrity)

### 12. Test vs Production Code Token Priority

**Risk:** Existing token budget algorithm selects files to include. Adding test generation may deprioritize production code in favor of test files, inverting the priority.

**What goes wrong:**
- Token budget includes existing test files but excludes production code
- Test generation context contains more test code than actual code to test
- Generated tests are based on other tests (not production code behavior)
- Context window wasted on irrelevant test fixtures
- Production code truncated to fit test file context

**Warning signs:**
- Generated tests import from existing test files (not production code)
- Token budget logs show test files taking majority of context
- Generated code quality degrades (less production code context available)
- Tests validate against test mocks instead of actual implementation
- File selection excludes modified production files but includes unrelated test files

**Prevention:**
- **Production-first token allocation:** Prioritize modified production files over existing test files in budget
- **Separate contexts:** Use different token budgets for code generation (needs prod files) vs test generation (needs prod + API docs)
- **Test file filtering:** Exclude existing test files from code generation context (they're not relevant)
- **Budget transparency:** Log which files included/excluded for both code and test generation
- **Smart file selection:** For test generation, include: modified prod file + its API signature + test examples (not all tests)

**Phase:** Phase 1 (Test Generation Architecture) - Token budget strategy must adapt

**References:**
- [LLM context management best practices](https://www.confident-ai.com/blog/llm-evaluation-metrics-everything-you-need-for-llm-evaluation)

### 13. Existing Test Suite Ignored

**Risk:** Repository already has tests. Test generation may duplicate existing tests, contradict existing patterns, or ignore existing test infrastructure entirely.

**What goes wrong:**
- Generated tests duplicate existing test coverage (wasted effort)
- Generated tests use different testing framework than existing tests
- Test naming/organization doesn't match existing patterns
- Generated tests conflict with existing test fixtures or mocks
- Existing test utilities/helpers not used by generated tests

**Warning signs:**
- Test count doubles but coverage doesn't increase proportionally
- Generated tests in wrong directory structure
- Generated tests don't import existing test utilities
- Existing and generated tests have different assertion styles
- CI runs two test frameworks (existing + generated using different tool)

**Prevention:**
- **Existing test analysis:** Before generating tests, analyze existing test files to extract patterns
- **Test framework detection:** Include existing test framework in generation prompt ("use pytest like existing tests")
- **Coverage-aware generation:** Only generate tests for uncovered code paths (check existing coverage first)
- **Pattern matching:** Extract test naming, organization patterns from existing tests and enforce in generation
- **Test utility reuse:** Identify existing test helpers/fixtures and instruct LLM to use them

**Phase:** Phase 1 (Test Generation Architecture) - Existing test analysis prerequisite

**References:**
- [Test code quality and patterns](https://www.researchgate.net/publication/273397841_Test_Code_Quality_and_Its_Relation_to_Issue_Handling_Performance)

### 14. Test Execution Timeout Tuning

**Risk:** Current test timeout from .booty.yml may be insufficient for generated test suites (which could be larger/slower than manual tests).

**What goes wrong:**
- Generated test suite exceeds timeout on first run
- Integration tests time out due to conservative timeout setting
- Timeout kills tests mid-execution, partial results interpreted as failures
- Different timeout needed for unit tests vs integration tests
- Timeout too generous, slow/hanging tests block pipeline

**Warning signs:**
- Tests consistently time out regardless of code quality
- Only first N tests execute before timeout
- Test execution time grows linearly with test count (near timeout limit)
- Integration tests always timeout but unit tests pass
- Refinement loop wastes iterations on timeout (not actual test failures)

**Prevention:**
- **Dynamic timeout scaling:** Calculate timeout based on test count (baseline + per-test allowance)
- **Test type timeouts:** Different timeouts for unit tests (fast) vs integration tests (slower)
- **Timeout budget monitoring:** Log timeout usage (50% = warning, 80% = consider increasing)
- **Per-test timeouts:** If framework supports it, enforce per-test timeout (not just suite timeout)
- **Timeout in test generation prompt:** Instruct LLM to generate fast tests that complete in <1s per test

**Phase:** Phase 2 (Test Execution Integration) - Timeout configuration critical for reliability

**References:**
- [Test timeout handling in automation](https://ghostinspector.com/blog/test-automation-mistakes/)

### 15. Draft PR Mental Model Confusion

**Risk:** Current behavior: draft PR if tests fail OR always draft for self-modification. Adding test generation changes mental model: is draft because "tests aren't generated yet" or "generated tests failed"?

**What goes wrong:**
- PR created as draft before tests generated (user confused why)
- Draft→ready promotion happens before tests fully validated
- Unclear to reviewers whether draft means "tests pending" or "tests failed"
- Self-modification PRs promoted despite being draft (logic bug)
- Users expect draft PRs to have tests but they're missing

**Warning signs:**
- Reviewers ask "where are the tests?" on draft PRs
- Draft PRs missing test files entirely
- PR promoted to ready before test generation completes
- PR labels don't distinguish "tests pending" vs "tests failed"
- Documentation unclear about draft PR lifecycle

**Prevention:**
- **Three-state model:** draft (tests pending) → draft (tests failed) → ready (tests passed)
- **PR labels:** Add "tests:generating", "tests:failed", "tests:passed" labels for transparency
- **PR body status:** Include "Test Generation: In Progress | Failed | Complete" section in PR body
- **Promotion guardrails:** Never promote draft→ready if tests haven't been generated yet
- **Clear commit history:** Separate commits for code changes vs test generation (reviewers see progression)

**Phase:** Phase 3 (PR Promotion Logic) - Status communication essential

**References:**
- [GitHub draft PR workflow](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/changing-the-stage-of-a-pull-request)

## Minor Pitfalls

### 16. Test File Naming Collisions

**Risk:** Generated test file names might collide with existing files or violate naming conventions.

**Prevention:** Extract test file naming pattern from existing tests, validate generated names don't collide before writing.

**Phase:** Phase 1

### 17. Excessive Test Generation for Trivial Changes

**Risk:** One-line bugfix generates 500 lines of tests (LLM over-generation).

**Prevention:** Include test scope guidance in prompt based on change size (1-line change = 1-2 tests, not comprehensive suite).

**Phase:** Phase 1

### 18. Test Generation Language Mismatch

**Risk:** Multi-language repos might get Python tests for TypeScript code (LLM confusion).

**Prevention:** Detect file language from extension, explicitly specify test language/framework in generation prompt.

**Phase:** Phase 1

### 19. Commit Message Noise

**Risk:** Commit messages include verbose test generation details.

**Prevention:** Keep commit message focused on production code changes, mention tests briefly ("with generated tests").

**Phase:** Phase 3

### 20. Test Generation for Deleted Files

**Risk:** LLM attempts to generate tests for files marked for deletion.

**Prevention:** Filter deleted files from test generation input (only generate tests for created/modified files).

**Phase:** Phase 1

## Summary: Top 3 Things to Get Right

### 1. Test Quality Over Quantity (Pitfall #1)
**Why Critical:** The entire value proposition collapses if generated tests provide false confidence. Must validate tests actually detect bugs.

**Mitigation:** Implement test quality gates before accepting generated tests. Require assertions, edge cases, negative tests. Consider mutation testing to verify tests can catch bugs.

**Impact:** Foundation for the feature. Everything else is worthless without quality tests.

### 2. One-Shot Test Generation, Code-Only Refinement (Pitfall #6)
**Why Critical:** Existing refinement loop is proven to work. Don't break it by introducing test regeneration churn.

**Mitigation:** Generate tests once after initial code generation, then freeze tests and refine only code during iterations. Tests should be stable anchor, not moving target.

**Impact:** Preserves existing system stability while adding new capability. Avoids infinite refinement loops.

### 3. Multi-Criteria PR Promotion (Pitfall #4)
**Why Critical:** Auto-promotion based solely on "tests passed" creates security bypass and false positive risks.

**Mitigation:** Require test pass + coverage threshold + quality checks + security scans before promotion. Never auto-promote self-modification PRs.

**Impact:** Prevents premature merges and maintains code quality gates. Balances automation with safety.

---

## Research Methodology

**Sources:**
- Web search for LLM test generation quality issues, flaky tests, automated PR promotion patterns
- Analysis of existing Booty architecture (generator.py, executor.py, pulls.py)
- Cross-reference with existing safety mechanisms (PathRestrictor, token budget, refinement loop)

**Confidence Levels:**
- **HIGH:** Integration pitfalls (#6-10) - directly analyzed existing code
- **MEDIUM:** Critical pitfalls (#1-5) - verified by multiple web sources, patterns validated
- **LOW:** Minor pitfalls (#16-20) - common sense extrapolations, not verified

**Key Assumptions:**
- Magentic LLM abstraction continues (test generation uses same pattern as code generation)
- PyGithub API remains primary GitHub interaction mechanism
- Fresh clone per task architecture preserved (no persistent workspace state)
- .booty.yml configuration extended to support test generation settings

---

*Researched: 2026-02-15*
*Confidence: MEDIUM (WebSearch verified with architectural analysis)*
*Primary focus: Integration with existing Builder pipeline*

## Sources

- [Benchmarking LLMs for Unit Test Generation](https://arxiv.org/pdf/2508.00408)
- [LLM Testing Methods and Strategies](https://www.confident-ai.com/blog/llm-testing-in-2024-top-methods-and-strategies)
- [LLM Evaluation Best Practices](https://langfuse.com/blog/2025-03-04-llm-evaluation-101-best-practices-and-challenges)
- [Common Test Automation Mistakes](https://testgrid.io/blog/common-mistakes-in-test-automation/)
- [Test Automation Pitfalls](https://testuff.com/automated-testing-pitfalls-common-mistakes-and-how-to-avoid-them/)
- [AI Code Generation Hallucinations](https://www.trendmicro.com/vinfo/us/security/news/vulnerabilities-and-exploits/the-mirage-of-ai-programming-hallucinations-and-code-integrity)
- [Package Hallucinations in AI Code](https://www.darkreading.com/application-security/ai-code-tools-widely-hallucinate-packages)
- [LLM Hallucinations in Code Review](https://diffray.ai/blog/llm-hallucinations-code-review/)
- [Test Coverage False Sense of Security](https://wearecommunity.io/communities/testautomation/articles/6307)
- [Code Coverage Manipulation](https://medium.com/@muhammedsaidkaya/false-sense-of-security-go-test-coverage-manipulation-in-sonarqube-ce-14acffc4206a)
- [Quality Over Quantity in Testing](https://dzone.com/articles/why-to-choose-quality-over-quantity-in-software-te)
- [Unit Testing Best Practices](https://www.augmentcode.com/guides/unit-testing-best-practices-that-focus-on-quality-over-quantity)
- [LLM Determinism Challenges](https://unstract.com/blog/understanding-why-deterministic-output-from-llms-is-nearly-impossible/)
- [Non-Determinism in LLM Settings](https://arxiv.org/html/2408.04667v5)
- [Defeating Non-Determinism in LLMs](https://www.flowhunt.io/blog/defeating-non-determinism-in-llms/)
- [Flaky Tests Management](https://www.ranorex.com/blog/flaky-tests/)
- [Flaky Tests in CI/CD](https://semaphore.io/community/tutorials/how-to-deal-with-and-eliminate-flaky-tests)
- [Flaky Test Detection with CI Tools](https://www.aviator.co/blog/flaky-tests-how-to-manage-them-practically/)
- [CI/CD Best Practices](https://www.digitalocean.com/community/tutorials/an-introduction-to-ci-cd-best-practices)
- [Fast Track Code Promotion](https://octopus.com/blog/fast-tracking-code-promotion-in-your-ci-cd-pipeline)
- [GitHub Reviewers Bypass Vulnerability](https://www.legitsecurity.com/blog/bypassing-github-required-reviewers-to-submit-malicious-code)
- [Code Review Security Standards](https://graphite.dev/guides/code-review-security-standards)
- [GitHub PR Changing Stage](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/changing-the-stage-of-a-pull-request)
- [GitHub Draft Pull Requests](https://ardalis.com/github-draft-pull-requests/)
- [Test Automation Challenges](https://www.testingmind.com/how-to-avoid-common-test-automation-challenges-and-failures/)
- [Code Quality Explained](https://blog.codacy.com/code-quality-explained)
- [Test Code Quality and Performance](https://www.researchgate.net/publication/273397841_Test_Code_Quality_and_Its_Relation_to_Issue_Handling_Performance)
