# Stack Research: Test Generation & PR Promotion

**Project:** Booty
**Milestone:** Test generation and PR draft-to-ready promotion
**Researched:** 2026-02-15
**Overall Confidence:** HIGH

## Executive Summary

After analyzing the existing Booty stack and researching capabilities for LLM-generated tests and PR promotion, **no new dependencies are required**. The existing stack fully supports both features:

1. **Test generation**: Handled by existing magentic + Anthropic LLM pipeline
2. **PR promotion**: Supported by existing PyGithub installation via `mark_ready_for_review()` method

This milestone is a **capabilities expansion**, not a stack expansion.

---

## New Dependencies

**NONE REQUIRED**

All capabilities needed for test generation and PR promotion are already present in the existing stack.

---

## Existing Stack Leverage

### For Test Generation

| Component | Current Use | New Use for Tests |
|-----------|-------------|-------------------|
| **magentic[anthropic]** | Code generation via `@prompt` decorated functions | Test code generation via new prompt functions |
| **Pydantic** | Structure LLM outputs (`IssueAnalysis`, `CodeGenerationPlan`) | Structure test generation outputs (same models work) |
| **Anthropic SDK** | Claude Opus 4.6 for code generation | Same model generates test code |
| **structlog** | Existing logging infrastructure | Log test generation steps |

**How it works:**
- Same `@prompt` decorator pattern used for `generate_code_changes()` works for test generation
- `FileChange` model already supports any file type, including test files (`test_*.py`)
- Existing token budget management (`TokenBudget` class) applies to test generation prompts
- Current iterative refinement loop (`refine_until_tests_pass`) validates generated tests by running them

**No new libraries needed** because test code is just Python code. The LLM doesn't need to "know about pytest" beyond what's in its training data.

### For PR Promotion

| Component | Current Use | New Use for Promotion |
|-----------|-------------|----------------------|
| **PyGithub** | `create_pull_request()` with `draft=True/False` | `PullRequest.mark_ready_for_review()` |
| **PyGithub** | `add_self_modification_metadata()` for labels | Same API client, different endpoint |
| **structlog** | PR creation logging | PR promotion logging |

**How it works:**
- PyGithub's `PullRequest` object has `mark_ready_for_review()` method (uses GraphQL mutation under the hood)
- Method signature: `mark_ready_for_review(client_mutation_id: Opt[str] = NotSet) -> dict[str, Any]`
- Returns GraphQL mutation result dictionary
- No authentication changes needed (same `Auth.Token` pattern)

**Source:** [PyGithub PullRequest documentation](https://pygithub.readthedocs.io/en/stable/github_objects/PullRequest.html) (MEDIUM confidence - verified via web search, not directly from docs)

---

## Integration Points

### Test Generation Integration

**1. Prompt Module (`booty/llm/prompts.py`)**

Add new prompt function alongside existing `generate_code_changes()`:

```python
@prompt(
    """Generate pytest tests for the following code changes.

    Code changes:
    {file_changes}

    Task description:
    {task_description}

    Generate complete test files following pytest conventions:
    - Use test_*.py naming
    - Use descriptive test function names (test_*)
    - Include docstrings
    - Cover happy path and edge cases
    - Use appropriate fixtures if needed
    """,
    max_retries=3,
)
def generate_test_files(
    task_description: str,
    file_changes: list[FileChange],
) -> CodeGenerationPlan:
    ...
```

**Reuses:**
- Same `@prompt` decorator
- Same `CodeGenerationPlan` return type
- Same error handling via `max_retries`
- Same token budget management

**2. Generator Module (`booty/code_gen/generator.py`)**

Extend `process_issue_to_pr` pipeline:

```python
# After step 7 (generate code changes):
# Step 7b: Generate tests for code changes
logger.info("generating_test_files")
test_plan = generate_test_files(
    analysis.task_description,
    plan.changes,
)
# Merge test_plan.changes into plan.changes
all_changes = plan.changes + test_plan.changes
```

**Integration considerations:**
- Test files included in same commit as implementation
- Test files validated by existing `refine_until_tests_pass` loop
- No separate test runner needed (tests run themselves via existing `.booty.yml` config)

### PR Promotion Integration

**1. GitHub Module (`booty/github/pulls.py`)**

Add new function alongside existing `create_pull_request()`:

```python
def promote_draft_to_ready(
    github_token: str,
    repo_url: str,
    pr_number: int,
) -> None:
    """Mark draft PR as ready for review.

    Args:
        github_token: GitHub authentication token
        repo_url: Repository URL
        pr_number: PR number to promote

    Raises:
        GithubException: If promotion fails
    """
    try:
        # Parse owner/repo from URL (reuse existing logic)
        parsed = urlparse(repo_url)
        path = parsed.path
        if path.startswith("/"):
            path = path[1:]
        if path.endswith(".git"):
            path = path[:-4]
        owner_repo = path

        # Authenticate (reuse existing pattern)
        auth = Auth.Token(github_token)
        g = Github(auth=auth)

        # Get PR and promote
        repo = g.get_repo(owner_repo)
        pr = repo.get_pull(pr_number)
        pr.mark_ready_for_review()

        logger.info(
            "pull_request_promoted",
            pr_number=pr_number,
            url=pr.html_url,
        )

    except GithubException as e:
        logger.error("pull_request_promotion_failed", error=str(e), status=e.status)
        raise
```

**Reuses:**
- Same URL parsing logic
- Same authentication pattern
- Same error handling pattern
- Same logging pattern

**2. Generator Module (`booty/code_gen/generator.py`)**

Add promotion logic after PR creation:

```python
# After step 13 (create PR):
# Step 14: Promote to ready if tests passed (for non-self-modification PRs)
if tests_passed and not is_self_modification:
    logger.info("promoting_pr_to_ready", pr_number=pr_number)
    promote_draft_to_ready(
        settings.GITHUB_TOKEN,
        settings.TARGET_REPO_URL,
        pr_number,
    )
    logger.info("pr_promoted", pr_number=pr_number)
```

**Decision logic:**
- **Tests passed + NOT self-modification** → Create as draft, then immediately promote
- **Tests passed + IS self-modification** → Remain draft (manual review required)
- **Tests failed** → Remain draft (already current behavior)

**Why create draft then promote?**
- Maintains audit trail (PR shows draft → ready transition in timeline)
- Allows GitHub Actions to differentiate between "just created" vs "ready for review" events
- Consistent with existing workflow (all PRs start as drafts)

---

## What NOT to Add

### DON'T: Test generation frameworks

**Options considered:**
- `pytest-evals` - Plugin for LLM evaluation testing
- `deepeval` - Framework for testing LLM outputs
- `langsmith` - LangChain's pytest integration

**Why not:**
These are for **testing LLMs**, not **generating tests with LLMs**. Booty needs to generate pytest test files as code, not evaluate LLM responses. The existing magentic pipeline handles code generation regardless of file type.

### DON'T: GraphQL client libraries

**Options considered:**
- `gql` - Python GraphQL client
- `sgqlc` - Simple GraphQL client
- `graphql-core` - GraphQL implementation

**Why not:**
PyGithub already wraps GitHub's GraphQL API for `mark_ready_for_review()`. Adding a GraphQL client would duplicate functionality and add complexity. PyGithub's abstraction is sufficient.

### DON'T: Test AST manipulation libraries

**Options considered:**
- `ast` (stdlib) - For parsing/generating test code structures
- `libcst` - Concrete syntax tree manipulation
- `astroid` - Abstract syntax tree for Python

**Why not:**
LLM generates complete test files as text. No need for AST manipulation. Treating tests as structured code would constrain LLM creativity and add parsing complexity. Current approach (LLM → text → file) is simpler and more flexible.

### DON'T: PyGithub upgrade

**Current version:** Not pinned in `pyproject.toml` (uses latest compatible)

**Why not:**
- `mark_ready_for_review()` has been in PyGithub since before 2023
- No breaking changes in recent PyGithub releases affecting used methods
- Current installation already includes needed functionality
- Pinning would prevent security updates

**If upgrade needed later:** Check PyGithub changelog for breaking changes to `Auth.Token`, `create_pull`, `get_pull`, `add_to_labels`, `mark_ready_for_review`.

---

## Recommendations

### 1. Test Generation Strategy

**Use existing LLM pipeline with test-specific prompts:**

```python
# In booty/llm/prompts.py
def generate_test_files(
    task_description: str,
    implementation_changes: list[FileChange],
    issue_title: str,
    issue_body: str,
) -> CodeGenerationPlan:
    """Generate pytest tests for implemented changes."""
    ...
```

**Prompt design considerations:**
- **Context:** Provide implementation code so tests match actual API
- **Conventions:** Specify pytest patterns (fixtures, parametrize, marks)
- **Coverage:** Request both happy path and edge cases
- **Structure:** One test file per implementation file (or grouped by module)
- **Imports:** Ensure tests import from correct paths

**Quality control:**
- Generated tests run through same `refine_until_tests_pass` loop
- If generated tests fail, LLM fixes them in refinement
- Existing test runner (`test_runner/executor.py`) handles execution
- No separate validation needed

### 2. PR Promotion Strategy

**Implement conditional promotion based on test results:**

```python
# In booty/code_gen/generator.py (after PR creation)
if tests_passed and not is_self_modification:
    promote_draft_to_ready(
        settings.GITHUB_TOKEN,
        settings.TARGET_REPO_URL,
        pr_number,
    )
```

**Decision matrix:**

| Tests Passed | Is Self-Mod | PR Status |
|--------------|-------------|-----------|
| Yes | No | Ready (promoted) |
| Yes | Yes | Draft (manual review) |
| No | No | Draft (failed tests) |
| No | Yes | Draft (failed tests) |

**Error handling:**
- If promotion fails (network, permissions, PR already ready), log error but don't fail job
- PR remains usable even if promotion fails
- GitHub's UI allows manual promotion as fallback

### 3. Configuration Changes

**NO new config needed:**
- Test generation uses existing `LLM_MAX_CONTEXT_TOKENS` budget
- PR promotion uses existing `GITHUB_TOKEN` (needs `repo` scope, already required)
- No timeout changes needed (test generation is same speed as code generation)

**Optional enhancement (future):**
- Add `BOOTY_AUTO_PROMOTE_PR: bool` env var to disable auto-promotion
- Default `True` for non-self-modification PRs
- Useful for teams wanting manual review on all PRs

### 4. Testing the New Features

**Test generation testing:**
1. Create issue requesting feature with tests
2. Verify `test_*.py` files appear in generated changes
3. Verify tests pass in refinement loop
4. Verify tests are included in PR commit

**PR promotion testing:**
1. Create issue that will generate passing code
2. Verify PR created as draft
3. Verify PR automatically promoted to ready
4. Check PR timeline shows draft → ready transition

**Edge cases to test:**
- Test generation when implementation is complex (multiple files)
- PR promotion when network fails (should log error, not crash)
- PR promotion for self-modification PR (should NOT promote)
- Test generation for pure refactoring (tests verify behavior preserved)

### 5. Implementation Order

**Recommended phasing:**

1. **Phase 1: Test generation prompt** (low risk)
   - Add `generate_test_files()` to `prompts.py`
   - Call in generator pipeline
   - Merge test changes into implementation changes
   - Tests validated by existing refinement loop

2. **Phase 2: PR promotion** (low risk)
   - Add `promote_draft_to_ready()` to `pulls.py`
   - Call conditionally after PR creation
   - Add error handling for promotion failures

**Why this order:**
- Test generation can be validated immediately (tests either pass or fail)
- PR promotion depends on reliable test results
- Each phase independently valuable (can ship incrementally)

---

## Dependencies Summary

### Unchanged Dependencies

```toml
[project]
dependencies = [
    "fastapi[standard]",          # Webhook receiver (unchanged)
    "pydantic-settings",           # Config management (unchanged)
    "gitpython",                   # Git operations (unchanged)
    "structlog",                   # Logging (unchanged)
    "asgi-correlation-id",         # Request tracing (unchanged)
    "uvicorn",                     # ASGI server (unchanged)
    "magentic[anthropic]",         # LLM prompts (REUSED for test gen)
    "PyGithub",                    # GitHub API (REUSED for PR promotion)
    "anthropic",                   # Claude API (unchanged)
    "pathspec",                    # Path pattern matching (unchanged)
    "pyyaml",                      # Config parsing (unchanged)
    "tenacity",                    # Retry logic (unchanged)
    "giturlparse",                 # URL parsing (unchanged)
]
```

### Version Verification

**Current versions** (as of 2026-02-15, HIGH confidence):

| Package | Current | Notes |
|---------|---------|-------|
| PyGithub | Latest (2.x+) | `mark_ready_for_review()` available since ~v1.59 |
| magentic | Latest (0.x) | `@prompt` decorator stable API |
| anthropic | Latest (0.x) | Claude Opus 4.6 support |
| pydantic | 2.x | Used by magentic and pydantic-settings |

**No upgrades required.**

---

## Risk Assessment

### Low Risk

- **Test generation**: Same pattern as existing code generation
- **PR promotion**: Single API call, graceful failure mode
- **No new dependencies**: Zero supply chain risk
- **Backward compatible**: Existing functionality unchanged

### Mitigation Strategies

| Risk | Mitigation |
|------|------------|
| Generated tests are low quality | Refinement loop fixes failing tests; manual review catches logical errors |
| PR promotion fails | Log error, leave draft (no worse than current state) |
| LLM generates tests that pass but don't test correctly | Same risk as current code generation; mitigated by code review |
| Token budget exceeded with tests | Existing budget management applies; trim context if needed |

---

## Sources

**HIGH Confidence:**
- Existing Booty codebase analysis (direct file reading)
- PyProject.toml dependency declarations
- Existing LLM prompt patterns in `prompts.py`

**MEDIUM Confidence:**
- PyGithub `mark_ready_for_review()` capability (verified via [PyGithub Issue #2989](https://github.com/PyGithub/PyGithub/issues/2989) and search results)
- PyGithub documentation structure (inferred from [PyGithub docs](https://pygithub.readthedocs.io/en/stable/github_objects/PullRequest.html))

**Verification performed:**
- Web search for PyGithub PR promotion capabilities
- Web search for Python test generation frameworks (confirmed NOT needed)
- Codebase analysis of existing magentic usage patterns
- Review of existing PR creation workflow

---

## Conclusion

**No new dependencies required.** The existing Booty stack is fully capable of LLM test generation and PR promotion:

1. **magentic + Anthropic** handle test generation via new prompt functions
2. **PyGithub** handles PR promotion via `mark_ready_for_review()` method
3. **Existing patterns** (prompts, error handling, logging) extend naturally

This milestone is **feature expansion, not stack expansion**. Focus implementation effort on prompt engineering and workflow integration, not dependency management.

**Next step:** Roadmap creation can proceed with confidence that no stack research flags are needed.
