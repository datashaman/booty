# Features Research: Test Generation & PR Promotion

**Domain:** LLM-powered test generation and automated PR promotion
**Researched:** 2026-02-15
**Context:** Subsequent milestone adding test generation and PR promotion to existing Builder agent

## Test Generation Features

### Table Stakes (Must-Have)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Unit test generation for changed files | Industry standard — automated testing tools always generate unit tests for code changes | Medium | LLM must understand file structure, identify testable functions/methods, generate assertions |
| Test execution before PR promotion | PR automation always runs tests before marking ready | Low | Already implemented — leverage existing test_runner.executor.execute_tests() |
| Test quality validation | LLM-generated tests need verification to avoid trivial/broken tests | High | Requires checking test assertions exist, tests actually execute, tests cover meaningful scenarios |
| Feedback loop on test failure | LLM must fix broken tests it generates | Medium | Iterative refinement already exists for code generation — apply same pattern to test generation |
| Test framework detection | Must use project's existing test framework (pytest, unittest, etc.) | Low | Check for test config files, existing test patterns |
| Correct test file placement | Tests must go in expected location (tests/, test_*.py pattern) | Low | Follow existing project convention or standard patterns |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Integration test generation where relevant | Most tools only generate unit tests; integration tests add real value | High | Requires understanding component boundaries, dependencies, realistic integration scenarios |
| Coverage-driven test generation | Generate tests to fill coverage gaps, not just blanket coverage | High | Requires running coverage analysis, identifying uncovered branches, targeting gaps |
| Edge case identification | LLM identifies and tests boundary conditions automatically | Medium | Prompts must guide LLM to consider edge cases (null, empty, negative, overflow, etc.) |
| Test data generation | Realistic test fixtures/data generated for tests | Medium | LLM creates meaningful test data instead of placeholder values |
| Mutation testing validation | Verify generated tests actually catch bugs by introducing mutations | Very High | Run mutations against generated tests to ensure they fail appropriately — resource intensive |
| Smart test selection | Only generate integration tests for files that interact with external systems | Medium | Analyze imports/dependencies to detect database, API, filesystem interactions |

### Anti-Features (Deliberately Avoid)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| 100% coverage mandate | Leads to trivial tests just to hit metrics; wastes resources | Target meaningful coverage — focus on critical paths, edge cases |
| Automated test deletion | Removing existing tests is dangerous — could delete important coverage | Only add/modify tests; preserve existing test suite |
| Generating tests without execution | Tests that don't run are worthless; must validate they work | Always execute generated tests before committing |
| Hardcoded test data | Makes tests brittle and environment-dependent | Use test fixtures, factories, or parameterized tests |
| Over-mocking in unit tests | Too many mocks means not testing real behavior | Mock only external dependencies; test real logic |
| Flaky test generation | Tests that pass/fail inconsistently break CI/CD | Validate tests run consistently multiple times before committing |

## PR Promotion Features

### Table Stakes (Must-Have)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Create PR as draft initially | Standard practice — PR not ready until tests pass | Low | Already supported — pulls.create_pull_request(draft=True) |
| Promote to ready when tests pass | Core automation pattern — all PR tools do this | Low | Use GitHub API to mark PR ready (gh pr ready or GraphQL mutation) |
| Wait for all CI checks to complete | Can't promote until status known | Medium | Listen for check_suite/check_run events or poll PR status |
| Status check validation | Verify required checks passed, not just any checks | Medium | Query branch protection rules for required checks |
| Handle concurrent PRs | Multiple PRs may be running simultaneously | Low | Already handled by existing job queue system |
| Logging PR promotion events | Audit trail for automation decisions | Low | Extend existing structlog logger |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Self-modification extra safety gates | Builder can modify itself — needs stronger promotion rules | Medium | Already partially implemented — extend with test requirements |
| Test quality gates for promotion | Don't promote if tests are trivial/low quality | High | Analyze test assertions, coverage delta, edge case coverage |
| Auto-comment on promotion | Explain why PR was promoted (which checks passed) | Low | Add comment to PR with status summary |
| Rollback on post-promotion failure | Demote back to draft if issues found after promotion | Medium | Monitor for new check failures after promotion |
| Reviewer assignment on promotion | Auto-assign reviewers when PR becomes ready | Low | Use pulls.add_self_modification_metadata pattern for all PRs |
| Smart promotion timing | Avoid promoting during off-hours for human review | Low | Check timestamp, only promote during working hours (configurable) |

### Anti-Features (Deliberately Avoid)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Auto-merge without human review | Dangerous for self-modification; bypasses code review | Promote to ready, require human merge approval |
| Force-push after promotion | Breaks GitHub's PR state; confusing for reviewers | Never force-push after PR created |
| Promotion before all checks complete | Premature promotion wastes reviewer time | Wait for definitive pass/fail on all checks |
| Ignoring branch protection rules | Bypassing security controls is dangerous | Respect all protection rules; fail loudly if can't promote |
| Silent failures | If promotion fails, automation should notify | Comment on PR when promotion blocked + log error |
| Promoting PRs with unresolved conversations | Dismisses reviewer feedback | Only technical checks should trigger promotion, not discussions |

## Complexity Assessment

### Low Complexity (1-2 days)
- Test framework detection
- Correct test file placement
- Create PR as draft initially
- Promote to ready when tests pass
- Logging PR promotion events
- Auto-comment on promotion
- Reviewer assignment on promotion
- Smart promotion timing

### Medium Complexity (3-5 days)
- Unit test generation for changed files
- Feedback loop on test failure
- Edge case identification
- Test data generation
- Smart test selection
- Wait for all CI checks to complete
- Status check validation
- Self-modification extra safety gates
- Rollback on post-promotion failure

### High Complexity (1-2 weeks)
- Test quality validation
- Integration test generation where relevant
- Coverage-driven test generation
- Test quality gates for promotion

### Very High Complexity (2+ weeks)
- Mutation testing validation

## Dependencies on Existing Features

### Test Generation Leverages

| Existing Feature | How It's Used |
|------------------|---------------|
| LLM prompts via magentic | Generate test code using same LLM prompt pattern as code generation |
| Test execution with iterative refinement | Run generated tests, feed failures back to LLM for fixes — already proven pattern |
| Fresh clone per task | Tests run in clean isolated workspace |
| Full file generation | Generate complete test files (not diffs) — matches existing code gen approach |
| Token budget management | Test generation prompts consume tokens — use existing budget tracking |
| pathspec for path restrictions | Ensure generated test files don't violate protected paths |

### PR Promotion Leverages

| Existing Feature | How It's Used |
|------------------|---------------|
| PR creation (as drafts) | Already creates draft PRs — extend with promotion logic |
| PyGithub integration | Use existing GitHub API client for PR status manipulation |
| Job queue with state tracking | Track PR state changes (draft → ready) alongside job state |
| Self-modification detection | Apply stricter promotion rules for self-targeted PRs |
| Logging infrastructure | Extend structlog for PR promotion events |
| Webhook listener | Could listen for check_suite events to trigger promotion (alternative to polling) |

## Feature Dependencies Graph

```
Test Generation Flow:
1. Analyze changed files (existing code analysis)
   ↓
2. Detect test framework (new: test framework detection)
   ↓
3. Generate unit tests (new: LLM test generation)
   ↓
4. Generate integration tests if relevant (new: smart test selection + LLM generation)
   ↓
5. Execute generated tests (existing: test_runner.executor)
   ↓
6. If tests fail → LLM fixes (existing: iterative refinement pattern)
   ↓
7. Validate test quality (new: test quality validation)
   ↓
8. Commit test files (existing: file writing)

PR Promotion Flow:
1. Create PR as draft (existing: pulls.create_pull_request with draft=True)
   ↓
2. Push commits triggers CI (GitHub Actions)
   ↓
3. Wait for checks to complete (new: status polling/webhook listening)
   ↓
4. Validate all required checks passed (new: check validation)
   ↓
5. Apply quality gates (new: test quality gates)
   ↓
6. Promote PR to ready (new: GitHub API call)
   ↓
7. Assign reviewers (existing pattern: pulls.add_self_modification_metadata)
   ↓
8. Add comment explaining promotion (new: comment generation)
```

## MVP Recommendation

For MVP (v1.1), prioritize:

**Must Build:**
1. Unit test generation for changed files
2. Test framework detection
3. Correct test file placement
4. Test execution before PR promotion (already exists)
5. Feedback loop on test failure (adapt existing pattern)
6. Create PR as draft initially (already exists)
7. Promote to ready when tests pass
8. Status check validation

**Nice to Have (if time allows):**
- Edge case identification in tests
- Auto-comment on promotion
- Smart test selection for integration tests

**Defer to v1.2+:**
- Coverage-driven test generation
- Test quality gates for promotion
- Mutation testing validation
- Rollback on post-promotion failure
- Integration test generation (start with unit tests only)

## Implementation Strategy

### Phase 1: Test Generation (Days 1-3)
- Detect test framework from project
- Generate unit tests for changed files using LLM
- Place tests in correct locations
- Execute tests with existing test_runner
- Apply iterative refinement on failures

### Phase 2: PR Promotion (Days 4-5)
- Wait for GitHub Actions checks to complete
- Validate required checks passed
- Promote PR from draft to ready
- Add promotion comment

### Phase 3: Quality & Polish (Days 6-7)
- Improve test generation prompts for edge cases
- Add test quality validation
- Handle edge cases (no tests generated, all tests fail, etc.)
- Integration testing of full pipeline

## Risk Factors

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Generated tests are trivial/useless | High | High | Test quality validation gate; human review can reject |
| LLM cannot fix failing tests | Medium | Medium | Limit retry attempts; fail job if tests still broken after N iterations |
| CI checks never complete (hung job) | Low | Medium | Add timeout to check waiting; fail after X minutes |
| Branch protection prevents promotion | Low | High | Check protection rules early; fail with clear error message |
| Generated tests are flaky | Medium | High | Run tests multiple times before committing; reject if inconsistent |
| Test generation exhausts token budget | Medium | Medium | Reserve token budget for tests; skip if budget insufficient |

## Success Criteria

Test generation succeeds when:
- [ ] Builder generates at least 1 unit test per changed file
- [ ] Generated tests execute without errors
- [ ] Generated tests include meaningful assertions (not just imports)
- [ ] Tests follow project's existing test conventions
- [ ] Tests pass before PR is promoted

PR promotion succeeds when:
- [ ] PR created as draft initially
- [ ] Promotion waits for all required checks
- [ ] PR promoted to ready only when checks pass
- [ ] Promotion logged with structured events
- [ ] Self-modification PRs apply extra safety gates
- [ ] Human can still manually promote if automation fails

---

## Sources

### Test Generation Research
- [LLM-Powered Test Case Generation: Enhancing Coverage and Efficiency](https://www.frugaltesting.com/blog/llm-powered-test-case-generation-enhancing-coverage-and-efficiency)
- [Mastering Test Automation with LLMs: A Step-by-Step Approach](https://www.frugaltesting.com/blog/mastering-test-automation-with-llms-a-step-by-step-approach)
- [LLM Testing in 2026: Top Methods and Strategies](https://www.confident-ai.com/blog/llm-testing-in-2024-top-methods-and-strategies)
- [LLMs for Automated Unit Test Generation and Assessment in Java](https://arxiv.org/html/2511.20403v1)
- [Unit Testing vs Integration Testing](https://circleci.com/blog/unit-testing-vs-integration-testing/)
- [Unit Testing vs. Integration Testing: AI's Role](https://www.qodo.ai/blog/unit-testing-vs-integration-testing-ais-role-in-redefining-software-quality/)
- [Automation Test Coverage: Metrics, Strategies, and Best Practices](https://www.ranorex.com/guide/improve-automation-test-coverage/)
- [JUnit Automated Test Case Generation and Code Coverage](https://www.parasoft.com/blog/code-coverage-and-automated-junit-test-case-generation/)

### PR Automation Research
- [Changing the stage of a pull request - GitHub Docs](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/changing-the-stage-of-a-pull-request)
- [How to automate testing in a pull request](https://graphite.com/guides/how-to-automate-testing-in-pull-request)
- [Pull Request Testing: A Complete Guide to QA Review Process](https://testquality.com/pull-request-testing-qa-pr-processes/)
- [Streamlining the pull request process with automation tools](https://graphite.dev/guides/streamlining-pull-request-process-automation)
- [Automatically merging a pull request - GitHub Docs](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request)
- [Auto-merge GitHub Pull Requests After GitHub Actions Pass](https://www.zonca.dev/posts/2025-10-20-github-actions-auto-merge)

### Anti-Patterns and Quality Research
- [Avoiding Test Automation Pitfalls: 5 Common Anti-Patterns](https://www.testdevlab.com/blog/5-test-automation-anti-patterns-and-how-to-avoid-them)
- [Software Testing Anti-patterns · Codepipes Blog](https://blog.codepipes.com/testing/software-testing-antipatterns.html)
- [8 Steps to Excel in Pull Request Testing Automation](https://www.startearly.ai/post/pull-request-testing-automation)
- [LLM Evaluation Metrics: The Ultimate LLM Evaluation Guide](https://www.confident-ai.com/blog/llm-evaluation-metrics-everything-you-need-for-llm-evaluation)
- [LLM Evaluation | IBM](https://www.ibm.com/think/insights/llm-evaluation)

### CI/CD Integration Research
- [How to Integrate Automation Testing into Your CI/CD Pipeline](https://www.frugaltesting.com/blog/how-to-integrate-automation-testing-into-your-ci-cd-pipeline)
- [CI/CD & The Need For Test Automation](https://testlio.com/blog/ci-cd-test-automation/)
- [What is automated testing in continuous delivery? | TeamCity](https://www.jetbrains.com/teamcity/ci-cd-guide/automated-testing/)

*Researched: 2026-02-15*
*Confidence: MEDIUM — WebSearch findings verified with official documentation where possible*
