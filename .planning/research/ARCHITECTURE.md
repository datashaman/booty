# Architecture Research: Test Generation & PR Promotion

**Milestone:** v1.1 Test Generation & PR Promotion
**Domain:** LLM-powered test generation integrated with existing Builder pipeline
**Researched:** 2026-02-15
**Confidence:** HIGH (existing pipeline architecture documented, GitHub API verified, test generation patterns researched)

## Current Pipeline

The existing Builder pipeline (from v1.0) follows this flow:

```
Webhook → Job Queue → Worker picks job → Clone repo →
  → Analyze issue (LLM) →
  → Generate code (LLM) →
  → Run tests → If fail: refine loop (max retries) →
  → Commit → Push → Create PR (draft if tests failed) →
  → Comment on issue if tests failed
```

**Key architectural components:**
- **FastAPI webhook gateway** - HMAC verification, event filtering, job enqueuing
- **Async job queue** - asyncio.Queue with worker pool, idempotency tracking
- **Builder pipeline** (`process_issue_to_pr` in `code_gen/generator.py`) - orchestrates full flow
- **LLM integration via magentic** - decorator-based prompt functions returning Pydantic models
- **Test runner** - subprocess execution with timeout, feeds errors back to LLM
- **PR creation via PyGithub** - REST API, creates draft PRs for self-targeted repos

**Data flow through LLM calls:**
1. `analyze_issue()` → `IssueAnalysis` (files to modify/create/delete, task description)
2. `generate_code_changes()` → `CodeGenerationPlan` (list of FileChange objects)
3. `refine_until_tests_pass()` → calls `regenerate_code_changes()` on test failures

**File change application:**
- Changes written to workspace immediately after generation
- Test runner executes against modified workspace
- If tests fail and LLM regenerates, files are rewritten in-place
- Final changes committed after refinement loop completes

## Modified Pipeline

Test generation and PR promotion integrate at two points in the existing pipeline:

```
Webhook → Job Queue → Worker picks job → Clone repo →
  → Analyze issue (LLM) →
  → Generate code AND TESTS (LLM) ← NEW: test generation integrated here →
  → Run tests (including generated tests) →
  → If fail: refine loop (regenerate code AND tests) ← NEW: tests included in refinement →
  → Commit (code + tests) → Push →
  → Create PR (draft) →
  → IF tests passed: Promote PR to ready-for-review ← NEW: PR promotion step →
  → ELSE: Comment on issue with failure details
```

**Key changes:**
1. **Test generation becomes part of code generation** - not a separate step
2. **Generated tests run in same test execution** - no separate test validation phase
3. **Tests included in refinement loop** - if tests fail, regenerate both code AND tests
4. **PR promotion is conditional final step** - only after successful test run

## Integration Points

### 1. Code Generation Phase (`generate_code_changes` prompt)

**Current behavior:**
- Prompt analyzes issue and generates FileChange objects for source code files
- Returns `CodeGenerationPlan` with `changes: list[FileChange]`

**Modified behavior:**
- Same prompt, extended to ALSO generate test files
- Returns `CodeGenerationPlan` with both source files AND test files in `changes`
- Test files identified by path pattern (e.g., `tests/test_*.py`, `*_test.py`)

**Integration approach:**
- Extend existing prompt template to request test generation
- Add instruction: "For each modified file, generate unit tests in tests/ directory"
- No new prompt function needed - just prompt template modification
- LLM already returns complete file contents, so test files work the same way

**Prompt modification location:** `src/booty/llm/prompts.py` - `_generate_code_changes_impl`

### 2. Test Refinement Loop (`regenerate_code_changes` prompt)

**Current behavior:**
- Analyzes test failures from error output
- Regenerates ONLY failing source files
- Returns `CodeGenerationPlan` with fixed files

**Modified behavior:**
- Analyzes test failures (could be from source OR generated tests)
- Decides whether to fix source code, fix tests, or both
- Returns `CodeGenerationPlan` with appropriate fixes

**Integration approach:**
- Extend prompt to understand that some failures may come from incorrect test generation
- Add instruction: "If test is wrong (not the code), regenerate the test file"
- LLM needs context to distinguish "test caught a bug" vs "test is incorrect"
- Leverage existing `failed_files` detection - already includes test files

**Prompt modification location:** `src/booty/llm/prompts.py` - `_regenerate_code_changes_impl`

### 3. PR Promotion (`create_pull_request` → promote)

**Current behavior:**
- Creates PR as draft if tests failed, ready-for-review otherwise
- For self-modification, ALWAYS creates draft (requires manual review)
- Returns PR number

**Modified behavior:**
- ALWAYS create PR as draft initially
- After PR created, if tests passed AND not self-modification: promote to ready-for-review
- Uses GitHub GraphQL API (REST doesn't support this operation)

**Integration approach:**
- Split PR creation into two steps:
  1. Create PR as draft (existing code)
  2. Conditionally promote to ready-for-review (new code)
- Add new function `promote_pr_to_ready()` in `src/booty/github/pulls.py`
- Call GraphQL API via PyGithub's `requester.graphql_named_mutation()`

**New function location:** `src/booty/github/pulls.py`
**Caller location:** `src/booty/code_gen/generator.py` - `process_issue_to_pr()` after PR creation

## New Components

### 1. Test Generation Prompt Enhancement (MODIFICATION, not new component)

**Location:** `src/booty/llm/prompts.py`

**Modification to `_generate_code_changes_impl` prompt:**
```python
@prompt(
    """You are a code generation assistant that produces working code based on GitHub issue requirements.

Your task is to generate COMPLETE file contents (not diffs) for the requested changes.
Additionally, generate unit tests for all modified or created source files.

[... existing prompt content ...]

Test Generation Requirements:
1. For each source file in changes, generate corresponding test file
2. Unit tests should cover main functionality and edge cases
3. Follow pytest conventions (test_*.py naming, test_* function names)
4. Include fixtures where appropriate
5. Tests should be in tests/ directory mirroring source structure
6. Integration tests only if the change involves multiple components
7. Mock external dependencies (API calls, database, filesystem)

Output both source files AND test files in the changes list.
""",
    max_retries=3,
)
```

**Why this works:**
- LLM already generates complete file contents
- Test files are just more FileChange objects
- Existing file writing logic handles test files automatically
- Test runner already executes all tests in workspace

### 2. PR Promotion Function (NEW component)

**Location:** `src/booty/github/pulls.py`

**Function signature:**
```python
def promote_pr_to_ready(
    github_token: str,
    repo_url: str,
    pr_number: int,
) -> None:
    """Promote a draft PR to ready-for-review using GitHub GraphQL API.

    Args:
        github_token: GitHub authentication token
        repo_url: Repository URL
        pr_number: PR number to promote

    Raises:
        GithubException: If promotion fails
    """
```

**Implementation approach:**
1. Parse repo owner/name from URL (reuse existing logic)
2. Get PR object via REST API to obtain node_id (GraphQL requires node ID)
3. Construct GraphQL mutation:
   ```graphql
   mutation {
     markPullRequestReadyForReview(input: {pullRequestId: "node_id"}) {
       pullRequest { id isDraft }
     }
   }
   ```
4. Execute via `github_client._Github__requester.requestJsonAndCheck()`
5. Log success/failure

**Dependencies:**
- PyGithub supports GraphQL via `Requester.requestJsonAndCheck()` with custom query
- Requires PR node_id (format: "PR_kwDOAbcdef123")
- Available in PyGithub since v1.55 (Booty uses v2.x)

## Data Flow Changes

### Before (v1.0):
```
1. analyze_issue() → IssueAnalysis
2. generate_code_changes() → CodeGenerationPlan with source files
3. Write source files to workspace
4. Run tests (existing tests from repo)
5. If fail: regenerate_code_changes() → CodeGenerationPlan with fixed source
6. Commit all changes
7. Create PR (draft if tests failed, ready if passed)
```

### After (v1.1):
```
1. analyze_issue() → IssueAnalysis
2. generate_code_changes() → CodeGenerationPlan with source files + test files
3. Write source + test files to workspace
4. Run tests (existing tests + generated tests)
5. If fail: regenerate_code_changes() → CodeGenerationPlan with fixed source or tests
6. Commit all changes (source + tests)
7. Create PR as draft (always start as draft)
8. If tests passed AND not self-modification:
     promote_pr_to_ready() → PR promoted
   Else:
     Leave as draft
```

**Key data flow insight:**
- Test files flow through existing FileChange → workspace write → git commit path
- No new data structures needed
- Test generation is "more of the same" from LLM's perspective

## Build Order (Implementation Sequence)

### Phase 1: Test Generation in Code Generation
**Goal:** LLM generates tests alongside code

1. **Modify `_generate_code_changes_impl` prompt** (`llm/prompts.py`)
   - Add test generation requirements to prompt
   - Specify pytest conventions, file structure
   - Request unit tests for all modified files

2. **Modify `_regenerate_code_changes_impl` prompt** (`llm/prompts.py`)
   - Add instruction to regenerate tests if they're incorrect
   - Include context about distinguishing test bugs vs code bugs

3. **Test manually:**
   - Create test issue requesting simple code change
   - Verify LLM generates both source and test files
   - Verify tests are syntactically valid
   - Verify test runner executes generated tests

**Validation criteria:**
- [ ] Generated tests appear in PR changes
- [ ] Generated tests are valid pytest files
- [ ] Test runner executes generated tests
- [ ] Generated tests cover basic functionality

### Phase 2: PR Promotion
**Goal:** Automatically promote draft PRs when tests pass

4. **Implement `promote_pr_to_ready()` function** (`github/pulls.py`)
   - Parse repo URL to get owner/name
   - Fetch PR to get node_id
   - Construct GraphQL mutation
   - Execute mutation via PyGithub requester
   - Add error handling and logging

5. **Integrate promotion into pipeline** (`code_gen/generator.py`)
   - After PR creation, check: tests_passed AND not is_self_modification
   - Call `promote_pr_to_ready()` if conditions met
   - Log promotion success/failure
   - Don't fail job if promotion fails (log warning instead)

6. **Update PR body formatting** (`github/pulls.py`)
   - Add note in PR body: "PR will be promoted to ready-for-review if tests pass"
   - Include test generation summary in PR body

**Validation criteria:**
- [ ] Draft PRs created for all jobs
- [ ] PRs promoted when tests pass (non-self-modification)
- [ ] PRs remain draft when tests fail
- [ ] PRs remain draft for self-modification (even if tests pass)
- [ ] Promotion logged correctly

### Phase 3: Integration Testing
**Goal:** Verify end-to-end behavior

7. **Test full pipeline with test generation:**
   - Issue requesting new feature → generates code + tests → tests pass → PR promoted
   - Issue with intentional test failure → generates code + tests → tests fail → PR remains draft → refinement regenerates → tests pass → PR promoted
   - Self-modification issue → generates code + tests → tests pass → PR remains draft

8. **Edge case testing:**
   - Code change that doesn't need tests (docs, config)
   - Code change where test generation fails but source is correct
   - Test timeout during generated test execution
   - GraphQL promotion failure (network error, permissions)

**Validation criteria:**
- [ ] End-to-end flow works for normal PRs
- [ ] End-to-end flow works for self-modification PRs
- [ ] Edge cases handled gracefully
- [ ] Errors logged appropriately

## Implementation Considerations

### 1. Test File Path Detection

**Challenge:** How does code know which FileChange objects are tests?

**Solution:** Path-based heuristic in `generator.py`:
```python
def is_test_file(path: str) -> bool:
    """Detect if file is a test based on path pattern."""
    return (
        path.startswith("tests/") or
        path.startswith("test/") or
        "/test_" in path or
        path.endswith("_test.py")
    )
```

**Usage:**
- PR body can separate source vs test changes
- Logging can distinguish test vs source file generation
- (Optional) Future: separate test section in commit message

### 2. Test Quality Validation

**Challenge:** Generated tests might be low quality or not run.

**Solution (existing architecture handles this):**
- Test runner executes ALL tests (including generated ones)
- If generated test is broken, test runner fails
- Refinement loop regenerates the test file
- If test never passes after max retries, PR opened as draft with failures

**No additional validation needed** - existing test-driven refinement handles it.

### 3. GraphQL API Authentication

**Challenge:** GraphQL requires different authentication than REST?

**Solution:** Same token works for both.
- PyGithub `Auth.Token(github_token)` works for GraphQL
- Use same `settings.GITHUB_TOKEN` already in config
- GraphQL endpoint: `https://api.github.com/graphql`
- PyGithub requester handles endpoint automatically

### 4. PR Node ID Retrieval

**Challenge:** GraphQL mutation needs PR node_id, not PR number.

**Solution:** Fetch PR object after creation:
```python
pr = repo.get_pull(pr_number)
node_id = pr.node_id  # Format: "PR_kwDOAbcdef123"
```

**Alternative:** Extract from PR creation response (already available).

### 5. Promotion Failure Handling

**Challenge:** What if PR promotion fails?

**Solution:** Non-fatal error.
- Log warning with error details
- Don't fail the job
- PR remains as draft (manual promotion possible)
- Post comment on issue noting promotion failed

**Rationale:** PR is already created and code is good. Promotion failure shouldn't invalidate the work.

### 6. Self-Modification Special Case

**Challenge:** Self-modification PRs should NEVER be auto-promoted (security).

**Solution (already exists):**
- `is_self_modification` flag passed to `process_issue_to_pr()`
- Promotion check: `if tests_passed and not is_self_modification:`
- Self-modification PRs require manual review regardless of test status

### 7. Test Generation Scope

**Challenge:** When to generate unit tests vs integration tests?

**Solution:** Prompt guidance + LLM judgment.
- Default: unit tests for all modified source files
- Integration tests only if change spans multiple components
- Prompt includes: "Generate integration tests if the change involves multiple components interacting"
- LLM decides based on code analysis

**Future enhancement:** Explicit test type specification in issue.

### 8. Generated Test File Structure

**Challenge:** Where should test files be placed?

**Solution:** Mirror source structure in tests/ directory.
- Source: `src/booty/code_gen/generator.py`
- Test: `tests/test_code_gen/test_generator.py`
- LLM prompt specifies: "Place tests in tests/ directory mirroring source structure"
- If source is `foo/bar.py`, test is `tests/test_foo/test_bar.py`

**Booty's existing structure:**
- Source in `src/booty/`
- Tests in root-level `tests/` (no src/ prefix in test paths)

## Architectural Patterns Applied

### Pattern: Extend Existing LLM Call (not add new one)

**Principle:** LLM already generating file contents - ask for more files, not a separate task.

**Application:**
- Generate tests in SAME prompt as code generation
- Both source and tests returned as FileChange objects
- No new data model, no new processing step

**Benefit:** Simpler architecture, tests have same context as code generation.

### Pattern: Leverage Existing Refinement Loop

**Principle:** Test failures already trigger refinement - generated test failures are no different.

**Application:**
- Generated tests run in same test execution as existing tests
- Failures from either trigger refinement
- Regeneration prompt can fix source OR tests

**Benefit:** No special handling for generated test failures.

### Pattern: Fail-Safe Promotion

**Principle:** Non-critical operations should not fail the job.

**Application:**
- PR promotion is last step, after all critical work done
- Promotion failure logged but job succeeds
- Manual promotion still possible

**Benefit:** Graceful degradation, no lost work.

### Pattern: GraphQL via Existing Client

**Principle:** Don't add dependencies when existing ones suffice.

**Application:**
- PyGithub supports GraphQL mutations
- Same authentication, same error handling
- No new dependency (e.g., gql library)

**Benefit:** Minimal surface area change, reuse existing patterns.

## Anti-Patterns Avoided

### Anti-Pattern: Separate Test Validation Phase

**Why avoid:** Adds complexity, duplicates test execution.

**Wrong approach:**
1. Generate code
2. Run tests
3. Generate tests
4. Run tests again to validate generated tests
5. Run all tests together

**Right approach (what we're doing):**
1. Generate code AND tests together
2. Run all tests once
3. Refinement handles any failures

### Anti-Pattern: New LLM Call for Test Generation

**Why avoid:** Context split, coordination overhead, more tokens used.

**Wrong approach:**
```python
code_plan = generate_code_changes(analysis, files)
test_plan = generate_tests_for_code(code_plan.changes)  # Separate LLM call
```

**Right approach (what we're doing):**
```python
plan = generate_code_changes(analysis, files)  # Returns source + tests
```

### Anti-Pattern: Synchronous PR Promotion

**Why avoid:** Blocks job completion on non-critical operation.

**Wrong approach:**
```python
pr_number = create_pull_request(...)
promote_pr_to_ready(pr_number)  # If this fails, whole job fails
```

**Right approach (what we're doing):**
```python
pr_number = create_pull_request(...)
try:
    promote_pr_to_ready(pr_number)
except Exception as e:
    logger.warning("promotion_failed", error=str(e))
    # Job continues, PR still exists
```

### Anti-Pattern: Test Generation Toggle

**Why avoid:** Partial features, configuration complexity.

**Wrong approach:**
```python
if settings.ENABLE_TEST_GENERATION:
    generate_tests()
```

**Right approach (what we're doing):**
- Always generate tests (it's a core feature)
- LLM already decides test scope based on code
- No configuration needed

## Scalability & Future Extensions

### Current Scope (v1.1)
- Generate unit tests for all code changes
- Integration tests when LLM determines necessary
- Promote non-self-modification PRs when tests pass

### Future Enhancements (post-v1.1)

**v1.2: Test Coverage Tracking**
- Run pytest with coverage
- Include coverage report in PR body
- Require minimum coverage threshold before promotion

**v1.3: Test Type Specification in Issue**
- Issue labels: `test:unit`, `test:integration`, `test:e2e`
- LLM generates specific test types based on labels

**v1.4: Selective Test Execution**
- Detect which tests need to run based on changed files
- Faster feedback in refinement loop

**v1.5: Test Quality Metrics**
- Analyze generated tests for quality (mocks, assertions, edge cases)
- Regenerate tests that don't meet quality threshold

## Security & Safety Considerations

### 1. Generated Test Execution
**Risk:** Generated tests could be malicious (arbitrary code execution).

**Mitigation:**
- Tests run in same workspace as generated code (already sandboxed)
- Same path restrictions apply to test files as source files
- Test files subject to same security review as source in PRs

### 2. Self-Modification with Generated Tests
**Risk:** Generated tests could bypass protected path validation.

**Mitigation:**
- Protected path validation runs BEFORE test generation
- Generated tests in tests/ directory (not protected paths)
- Self-modification PRs always require manual review

### 3. PR Auto-Promotion
**Risk:** Bad code auto-promoted because tests are too permissive.

**Mitigation:**
- Self-modification NEVER auto-promoted
- Promotion only happens if ALL tests pass (existing + generated)
- Quality checks (ruff) still run for self-modification
- Manual review always option via draft PR

## Sources

### LLM Test Generation Research
- [Choosing LLMs to generate high-quality unit tests for code | Red Hat Research](https://research.redhat.com/blog/2025/04/21/choosing-llms-to-generate-high-quality-unit-tests-for-code/)
- [Automating Test Driven Development with LLMs | Medium](https://medium.com/@benjamin22-314/automating-test-driven-development-with-llms-c05e7a3cdfe1)
- [GitHub - githubnext/testpilot: Test generation using large language models](https://github.com/githubnext/testpilot)
- [How to Use AI to Automate Unit Testing with TestGen-LLM and Cover-Agent](https://www.freecodecamp.org/news/automated-unit-testing-with-testgen-llm-and-cover-agent/)
- [LLM Testing in 2026: Top Methods and Strategies - Confident AI](https://www.confident-ai.com/blog/llm-testing-in-2024-top-methods-and-strategies)

### GitHub API Research
- [Is there is a REST API to convert a draft pull request to Ready to Review? | GitHub Community Discussion](https://github.com/orgs/community/discussions/70061)
- [How to "Ready to Review" / undraft pull request | hub4j/github-api Discussion](https://github.com/hub4j/github-api/discussions/1578)
- [gh pr ready | GitHub CLI Manual](https://cli.github.com/manual/gh_pr_ready)
- [Github GraphQL — PyGithub Documentation](https://pygithub.readthedocs.io/en/stable/graphql.html)
- [Mutations - GitHub GraphQL API Docs](https://docs.github.com/en/graphql/reference/mutations)

### Pytest Integration Research
- [LLM Testing: A Practical Guide to Automated Testing for LLM Applications - Langfuse Blog](https://langfuse.com/blog/2025-10-21-testing-llm-applications)
- [GitHub - AlmogBaku/pytest-evals: A pytest plugin for running and analyzing LLM evaluation tests](https://github.com/AlmogBaku/pytest-evals)
- [Pytest is All You Need - LLMs for Engineers](https://arjunbansal.substack.com/p/pytest-is-all-you-need)

---

*Researched: 2026-02-15*
*Confidence: HIGH - existing architecture well-documented, GitHub API capabilities verified, test generation patterns researched*
