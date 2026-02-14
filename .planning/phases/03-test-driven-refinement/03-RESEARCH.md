# Phase 3: Test-Driven Refinement - Research

**Researched:** 2026-02-14
**Domain:** Test execution, subprocess management, retry strategies, configuration validation
**Confidence:** HIGH

## Summary

Test-driven refinement requires running external test commands in isolated subprocesses, capturing their output, parsing failures intelligently, and feeding relevant error context back to an LLM for targeted regeneration. The phase builds on existing Python asyncio patterns and extends the current `process_issue_to_pr` pipeline with a test-and-refine loop.

The standard approach uses `asyncio.create_subprocess_shell()` with `asyncio.wait_for()` for timeout control, PyYAML for configuration parsing with Pydantic validation, the built-in `traceback` module for error extraction, and either tenacity or backoff for retry logic with exponential backoff. The project already uses PyGithub which provides native support for draft PRs and issue comments.

**Primary recommendation:** Use asyncio subprocess with wait_for timeouts, PyYAML + Pydantic for .booty config validation, built-in traceback parsing for error extraction, tenacity for retry logic, and extend existing PyGithub patterns for GitHub API interactions.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncio.subprocess | stdlib | Subprocess execution with async/await | Built-in, integrates with existing async codebase, proper timeout and signal handling |
| PyYAML | 6.0+ | YAML parsing | Simple, widely adopted, sufficient for config file parsing |
| pydantic | 2.x (already in project) | Config schema validation | Already used via pydantic-settings, type-safe validation with clear error messages |
| traceback | stdlib | Parse exception tracebacks | Built-in, provides StackSummary and frame extraction for identifying error locations |
| tenacity | 8.x | Retry logic with exponential backoff | De facto standard for retry patterns, supports asyncio, configurable strategies |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathspec | latest (already in project) | Gitignore-style pattern matching | Already used for path security, can help identify test files |
| PyGithub | latest (already in project) | GitHub API interactions | Already used, has draft PR and issue comment support |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyYAML | ruamel.yaml | ruamel supports YAML 1.2 and comment preservation, but PyYAML 6.0+ is simpler and sufficient for read-only config parsing |
| tenacity | backoff | backoff has cleaner decorator API, but tenacity has better asyncio integration and more flexible stop/wait strategies |
| asyncio.subprocess | subprocess.run() | subprocess.run() is simpler but blocks, incompatible with existing async architecture |

**Installation:**
```bash
pip install pyyaml tenacity
```

## Architecture Patterns

### Recommended Project Structure
```
src/booty/
├── test_runner/           # New module for test execution
│   ├── __init__.py
│   ├── config.py          # .booty config schema and loading
│   ├── executor.py        # Subprocess execution with timeout
│   └── parser.py          # Test output parsing and error extraction
├── code_gen/
│   ├── generator.py       # Existing, extend with refinement loop
│   └── refiner.py         # New: targeted regeneration logic
└── github/
    ├── pulls.py           # Existing, extend with draft PR support
    └── comments.py        # New: issue comment formatting
```

### Pattern 1: Async Subprocess with Timeout

**What:** Execute test commands with configurable timeout using asyncio
**When to use:** All test executions in the refinement loop

**Example:**
```python
# Source: https://docs.python.org/3/library/asyncio-subprocess.html
import asyncio

async def run_tests_with_timeout(
    command: str,
    timeout: int,
    cwd: str
) -> tuple[int, str, str]:
    """Run test command with timeout.

    Returns:
        (exit_code, stdout, stderr)

    Raises:
        asyncio.TimeoutError: If command exceeds timeout
    """
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout
        )
        return proc.returncode, stdout.decode(), stderr.decode()
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()  # Clean up zombie process
        raise
```

### Pattern 2: YAML Config with Pydantic Validation

**What:** Load and validate .booty YAML config file with type safety
**When to use:** At start of test-driven refinement phase

**Example:**
```python
# Source: https://medium.com/better-programming/validating-yaml-configs-made-easy-with-pydantic-594522612db5
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
import yaml

class BootyConfig(BaseModel):
    """Schema for .booty.yml configuration."""

    test_command: str = Field(..., description="Command to run tests")
    timeout: int = Field(default=300, ge=10, le=3600, description="Test timeout in seconds")
    max_retries: int = Field(default=3, ge=1, le=10, description="Max refinement attempts")

    @field_validator('test_command')
    @classmethod
    def validate_command_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("test_command cannot be empty")
        return v.strip()

def load_booty_config(workspace_path: Path) -> BootyConfig:
    """Load and validate .booty.yml from workspace root.

    Raises:
        FileNotFoundError: If .booty.yml doesn't exist
        ValidationError: If config is invalid
    """
    config_path = workspace_path / ".booty.yml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"No .booty.yml found in {workspace_path}. "
            "Cannot proceed without test configuration."
        )

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return BootyConfig.model_validate(data)
```

### Pattern 3: Traceback Parsing for File Identification

**What:** Extract file paths from traceback to identify which files caused failures
**When to use:** After test failure to determine what to regenerate

**Example:**
```python
# Source: https://docs.python.org/3/library/traceback.html
import traceback
from pathlib import Path

def extract_files_from_traceback(
    stderr: str,
    workspace_path: Path
) -> set[str]:
    """Extract workspace-relative file paths from test output.

    Parses traceback-like output and identifies files that are:
    1. Inside the workspace
    2. Not in test directories (to find source files, not test files)

    Args:
        stderr: Test command stderr output
        workspace_path: Absolute path to workspace root

    Returns:
        Set of workspace-relative file paths involved in failure
    """
    involved_files = set()

    # Simple heuristic: extract lines that look like file references
    # Format: "  File \"/path/to/file.py\", line 123, in function_name"
    for line in stderr.split('\n'):
        line = line.strip()
        if line.startswith('File "') and '", line ' in line:
            # Extract path between quotes
            start = line.find('"') + 1
            end = line.find('"', start)
            file_path = Path(line[start:end])

            # Only include files inside workspace
            try:
                relative = file_path.relative_to(workspace_path)
                # Exclude test files (we want source files)
                if 'test' not in str(relative).lower():
                    involved_files.add(str(relative))
            except ValueError:
                # File not in workspace, skip
                continue

    return involved_files
```

### Pattern 4: Retry with Exponential Backoff

**What:** Retry test execution with increasing delays for transient errors
**When to use:** For API timeouts, rate limits (not test failures - those use fixed retry count)

**Example:**
```python
# Source: https://tenacity.readthedocs.io/
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)
import asyncio
from anthropic import RateLimitError, APITimeoutError

@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, asyncio.TimeoutError)),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def regenerate_with_retry(prompt: str, model) -> str:
    """Regenerate code with retry for transient API errors.

    Retries with exponential backoff: 4s, 8s, 16s, 32s, 60s (max)
    Only retries on transient errors, not validation failures.
    """
    return await model.generate(prompt)
```

### Pattern 5: Targeted Refinement Loop

**What:** Retry loop that feeds failures back and regenerates only affected files
**When to use:** Main orchestrator for test-driven refinement phase

**Example:**
```python
async def refine_until_tests_pass(
    workspace: Workspace,
    config: BootyConfig,
    initial_changes: list[FileChange],
    settings: Settings,
) -> tuple[bool, list[FileChange], str | None]:
    """Iteratively refine code until tests pass or max retries exceeded.

    Returns:
        (tests_passed, final_changes, error_message)
    """
    current_changes = initial_changes

    for attempt in range(1, config.max_retries + 1):
        logger.info("test_attempt", attempt=attempt, max=config.max_retries)

        # Apply current changes to workspace
        apply_changes_to_workspace(workspace.path, current_changes)

        # Run tests
        try:
            exit_code, stdout, stderr = await run_tests_with_timeout(
                config.test_command,
                config.timeout,
                workspace.path,
            )
        except asyncio.TimeoutError:
            error_msg = f"Tests exceeded timeout of {config.timeout}s"
            logger.warning("test_timeout", attempt=attempt, timeout=config.timeout)

            if attempt == config.max_retries:
                return False, current_changes, error_msg

            # Feed timeout back to LLM for optimization
            current_changes = await regenerate_for_timeout(
                current_changes,
                config.timeout,
                settings
            )
            continue

        # Tests passed!
        if exit_code == 0:
            logger.info("tests_passed", attempt=attempt)
            return True, current_changes, None

        # Tests failed - analyze and regenerate
        logger.warning("tests_failed", attempt=attempt, exit_code=exit_code)

        if attempt == config.max_retries:
            # Final attempt failed
            error_summary = extract_error_summary(stderr, stdout)
            return False, current_changes, error_summary

        # Extract relevant error context
        error_context = extract_test_failures(stderr, stdout)

        # Identify files involved in failure
        failed_files = extract_files_from_traceback(stderr, workspace.path)

        # Regenerate only affected files
        current_changes = await regenerate_failed_files(
            failed_files,
            error_context,
            current_changes,
            settings,
        )

    # Should never reach here
    return False, current_changes, "Max retries exceeded"
```

### Anti-Patterns to Avoid

- **Cumulative context:** Don't feed all previous attempts to LLM - keeps each iteration lean with only most recent failure
- **Full regeneration:** Don't regenerate all files on every failure - analyze traceback to target only affected files
- **Raw output dumps:** Don't send entire test output to LLM - extract relevant tracebacks and assertion errors only
- **Blocking subprocess:** Don't use `subprocess.run()` - breaks async architecture and prevents concurrent job processing
- **Manual retry loops:** Don't hand-roll retry logic for API calls - use tenacity for proper exponential backoff

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subprocess timeout | Manual threading or signal handlers | `asyncio.wait_for()` | Proper cleanup, no zombie processes, integrates with event loop |
| Retry with backoff | Custom sleep loop | `tenacity` library | Handles edge cases (jitter, max time, exception filtering), battle-tested |
| YAML parsing | String manipulation or regex | `yaml.safe_load()` | Handles escaping, types, anchors, security (no arbitrary code execution) |
| Config validation | Manual isinstance checks | Pydantic models | Type coercion, nested validation, clear error messages with field paths |
| Traceback parsing | Regex on formatted strings | `traceback.extract_tb()` | Reliable frame extraction, handles edge cases, version-compatible |
| Draft PR creation | GitHub REST API manually | PyGithub `pr.convert_to_draft()` | Abstracts GraphQL complexity, handles auth, retries |

**Key insight:** Test execution and retry logic have subtle failure modes (zombie processes, thundering herd, rate limit cascades). Use standard libraries that handle these edge cases rather than reimplementing them.

## Common Pitfalls

### Pitfall 1: Zombie Processes from Timeout

**What goes wrong:** When timeout occurs, subprocess is killed but not waited for, creating zombie processes that accumulate over time.

**Why it happens:** `proc.kill()` sends SIGKILL but doesn't reap the process. Without `await proc.wait()`, the process stays in zombie state until parent exits.

**How to avoid:**
```python
try:
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
except asyncio.TimeoutError:
    proc.kill()
    await proc.wait()  # CRITICAL: reap the zombie
    raise
```

**Warning signs:** Increasing number of processes in 'Z' state, memory not being freed after timeouts

### Pitfall 2: Context Explosion with Cumulative History

**What goes wrong:** Feeding all previous attempts and failures to LLM causes token budget overflow and degraded performance.

**Why it happens:** Well-intentioned attempt to give LLM "full context" for learning from mistakes.

**How to avoid:** Last-attempt-only pattern - each iteration sees only:
- Current code
- Most recent failure output
- Original issue requirements

**Warning signs:** LLM requests timing out, tokens exceeded errors, generic/vague regenerations

### Pitfall 3: Test Timeout vs API Timeout Confusion

**What goes wrong:** Using same retry strategy for test failures (deterministic, should retry N times) and API timeouts (transient, need exponential backoff).

**Why it happens:** Both raise exceptions, easy to catch together.

**How to avoid:** Separate retry strategies:
- Test failures: Fixed retry count from .booty config
- API errors: Exponential backoff with tenacity

**Warning signs:** Rapid retry exhaustion on API rate limits, excessive delays on test failures

### Pitfall 4: Missing .booty Config Silent Fallback

**What goes wrong:** Code runs default test command when .booty.yml is missing, potentially running wrong tests or none at all.

**Why it happens:** Attempting to be "helpful" with fallback defaults.

**How to avoid:** Fail fast and explicitly when .booty.yml doesn't exist:
```python
if not config_path.exists():
    raise FileNotFoundError(
        f"No .booty.yml found. Cannot proceed without test configuration."
    )
```

**Warning signs:** PRs created without test validation, inconsistent test execution across repos

### Pitfall 5: Shell Injection via Unchecked Test Command

**What goes wrong:** Malicious .booty.yml in target repo could execute arbitrary commands via shell injection.

**Why it happens:** Using `create_subprocess_shell()` without sanitization.

**How to avoid:**
- Accept risk - .booty.yml is in target repo which we already trust (we execute its tests)
- Document: .booty.yml is trusted configuration, not user input
- Workspace isolation provides container boundary

**Warning signs:** Complex shell commands with pipes/redirects in .booty.yml, unexpected network activity during tests

### Pitfall 6: Over-Trimming Test Output

**What goes wrong:** Aggressive filtering removes context LLM needs to understand failure.

**Why it happens:** Fear of token budget overflow.

**How to avoid:** Preserve critical context:
- Full traceback (not just last line)
- Assertion failure messages
- First 5-10 lines of output before error
- Trim only repeated stack frames and verbose logging

**Warning signs:** LLM unable to identify root cause, requests for "more information" in regenerated code

## Code Examples

### Complete Test Runner Module

```python
# src/booty/test_runner/executor.py
"""Test execution with subprocess and timeout handling."""
import asyncio
from dataclasses import dataclass
from pathlib import Path
from booty.logging import get_logger

logger = get_logger()


@dataclass
class TestResult:
    """Result of test execution."""
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


async def execute_tests(
    command: str,
    timeout: int,
    workspace_path: Path,
) -> TestResult:
    """Execute test command with timeout.

    Args:
        command: Shell command to execute
        timeout: Timeout in seconds
        workspace_path: Working directory for command execution

    Returns:
        TestResult with exit code and output

    Raises:
        Never raises - captures all failures in TestResult
    """
    logger.info("executing_tests", command=command, timeout=timeout)

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace_path),
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            return TestResult(
                exit_code=proc.returncode,
                stdout=stdout_bytes.decode('utf-8', errors='replace'),
                stderr=stderr_bytes.decode('utf-8', errors='replace'),
                timed_out=False,
            )

        except asyncio.TimeoutError:
            logger.warning("test_timeout_killing_process", timeout=timeout)
            proc.kill()
            await proc.wait()  # Prevent zombie

            return TestResult(
                exit_code=-1,
                stdout="",
                stderr=f"Test execution exceeded timeout of {timeout} seconds",
                timed_out=True,
            )

    except Exception as e:
        logger.error("test_execution_error", error=str(e), exc_info=True)
        return TestResult(
            exit_code=-1,
            stdout="",
            stderr=f"Test execution failed: {str(e)}",
            timed_out=False,
        )
```

### Config Loading with Validation

```python
# src/booty/test_runner/config.py
"""Configuration schema and loading for .booty.yml files."""
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
import yaml

class BootyConfig(BaseModel):
    """Schema for .booty.yml configuration file."""

    test_command: str = Field(
        ...,
        description="Shell command to run tests (e.g., 'pytest tests/')",
    )

    timeout: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Maximum test execution time in seconds",
    )

    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of refinement attempts before giving up",
    )

    @field_validator('test_command')
    @classmethod
    def validate_command_not_empty(cls, v: str) -> str:
        """Ensure test command is not empty or whitespace."""
        if not v.strip():
            raise ValueError("test_command cannot be empty")
        return v.strip()


def load_booty_config(workspace_path: Path) -> BootyConfig:
    """Load and validate .booty.yml from workspace root.

    Args:
        workspace_path: Path to workspace root directory

    Returns:
        Validated BootyConfig instance

    Raises:
        FileNotFoundError: If .booty.yml doesn't exist
        yaml.YAMLError: If YAML is malformed
        ValidationError: If config schema is invalid
    """
    config_path = workspace_path / ".booty.yml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"No .booty.yml configuration found in {workspace_path}. "
            "Test-driven refinement requires a .booty.yml file specifying "
            "how to run tests. Example:\n\n"
            "test_command: pytest tests/\n"
            "timeout: 300\n"
            "max_retries: 3\n"
        )

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(".booty.yml is empty")

    return BootyConfig.model_validate(data)
```

### Error Context Extraction

```python
# src/booty/test_runner/parser.py
"""Parse test output to extract relevant error context."""
from pathlib import Path


def extract_error_summary(stderr: str, stdout: str, max_lines: int = 100) -> str:
    """Extract concise error summary from test output.

    Prioritizes:
    1. Assertion errors with context
    2. Traceback information
    3. Test failure summaries

    Removes:
    - Verbose logging
    - Repeated stack frames
    - Test discovery output

    Args:
        stderr: Test stderr output
        stdout: Test stdout output
        max_lines: Maximum lines to include

    Returns:
        Filtered error summary suitable for LLM context
    """
    lines = []

    # Combine stderr and stdout
    combined = stderr + "\n" + stdout

    # Split into lines
    output_lines = combined.split('\n')

    # Simple heuristic: keep lines that look like errors
    in_traceback = False
    for line in output_lines:
        stripped = line.strip()

        # Start of traceback
        if stripped.startswith('Traceback (most recent call last):'):
            in_traceback = True
            lines.append(line)
            continue

        # Traceback frame
        if in_traceback and (stripped.startswith('File "') or stripped.startswith('  ')):
            lines.append(line)
            continue

        # Error line (ends traceback)
        if in_traceback and stripped and not stripped.startswith(' '):
            lines.append(line)
            in_traceback = False
            continue

        # Assertion errors
        if 'AssertionError' in line or 'assert' in line.lower():
            lines.append(line)
            continue

        # Test failure summaries (pytest format)
        if stripped.startswith('FAILED ') or stripped.startswith('ERROR '):
            lines.append(line)
            continue

        # Summary lines
        if ' failed' in line.lower() or ' error' in line.lower():
            lines.append(line)
            continue

    # Limit to max_lines
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"\n... (truncated {len(lines) - max_lines} lines)"]

    return '\n'.join(lines)


def extract_files_from_output(
    output: str,
    workspace_path: Path,
) -> set[str]:
    """Extract file paths mentioned in test output.

    Parses traceback-style references and identifies workspace files.
    Excludes test files to focus on source code that needs fixing.

    Args:
        output: Combined test output (stderr + stdout)
        workspace_path: Absolute path to workspace root

    Returns:
        Set of workspace-relative paths involved in failures
    """
    involved_files = set()

    # Pattern: File "/path/to/file.py", line 123
    for line in output.split('\n'):
        stripped = line.strip()
        if stripped.startswith('File "') and '", line ' in stripped:
            # Extract path between quotes
            start = stripped.find('"') + 1
            end = stripped.find('"', start)
            file_path = Path(stripped[start:end])

            # Convert to workspace-relative if inside workspace
            try:
                relative = file_path.relative_to(workspace_path)
                relative_str = str(relative)

                # Exclude test files - we want to fix source, not tests
                if not any(part.startswith('test') for part in relative.parts):
                    involved_files.add(relative_str)
            except ValueError:
                # File outside workspace, skip
                continue

    return involved_files
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| subprocess.Popen() with threading | asyncio.create_subprocess_shell() | Python 3.4+ | Non-blocking subprocess execution, integrates with event loop |
| Manual retry loops with time.sleep() | tenacity/backoff decorators | ~2016 (tenacity 4.0) | Declarative retry strategies, proper jitter, exponential backoff |
| PyYAML 3.x (unsafe yaml.load) | PyYAML 6.0+ (yaml.safe_load default) | 2021 | Security: prevents arbitrary code execution from YAML |
| Pydantic v1 | Pydantic v2 | 2023 | 5-50x faster validation, better error messages, strict mode |
| GitHub REST API for draft PRs | PyGithub with GraphQL | 2019 (draft PR feature) | Simplified API, PyGithub abstracts GraphQL complexity |

**Deprecated/outdated:**
- `subprocess.call()` with timeout via threading: Use `asyncio.wait_for()` instead
- `yaml.load()` without Loader: Use `yaml.safe_load()` to prevent code execution
- String-based config validation: Use Pydantic models for type safety and clear errors
- Manual traceback formatting: Use `traceback.extract_tb()` for structured frame access

## Open Questions

1. **How to handle flaky tests?**
   - What we know: Tests may fail intermittently due to timing issues
   - What's unclear: Should we retry test execution itself (not just code regeneration)?
   - Recommendation: Start without test execution retries - treat flaky tests as code issues for LLM to fix (add sleeps, fix race conditions). Can add test retry in v2 if needed.

2. **What if failure involves no traceback (e.g., compilation error)?**
   - What we know: Not all test failures produce Python tracebacks (syntax errors, import errors)
   - What's unclear: How to identify files to regenerate without traceback?
   - Recommendation: Fall back to analyzing error message text and regenerating all originally modified files

3. **Should we preserve test output across attempts?**
   - What we know: Each attempt sees only latest failure (not cumulative)
   - What's unclear: Should we log all attempts for debugging/analytics?
   - Recommendation: Log each attempt's output to structured logs for observability, but don't send to LLM

4. **What about repos without tests?**
   - What we know: .booty.yml is required
   - What's unclear: Should we support "no-op" test command for repos that don't want validation?
   - Recommendation: Require real test command - no .booty.yml means no Phase 3 (PR created in draft mode from Phase 2)

## Sources

### Primary (HIGH confidence)

- [Python asyncio subprocess documentation](https://docs.python.org/3/library/asyncio-subprocess.html) - Subprocess execution, timeout handling, output capture
- [Python traceback module documentation](https://docs.python.org/3/library/traceback.html) - StackSummary, extract_tb, programmatic traceback parsing
- [Tenacity documentation](https://tenacity.readthedocs.io/) - Retry strategies, exponential backoff, asyncio support
- [PyGithub PullRequest documentation](https://pygithub.readthedocs.io/en/latest/github_objects/PullRequest.html) - Draft PR conversion methods
- [PyGithub Issue documentation](https://pygithub.readthedocs.io/en/latest/github_objects/Issue.html) - Issue comment creation
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html) - Timeout behavior, process cleanup

### Secondary (MEDIUM confidence)

- [How to Validate YAML Configs Using Pydantic](https://medium.com/better-programming/validating-yaml-configs-made-easy-with-pydantic-594522612db5) - Pydantic + YAML pattern
- [pytest output management documentation](https://docs.pytest.org/en/stable/how-to/output.html) - Traceback formatting options
- [Understanding the Python Traceback – Real Python](https://realpython.com/python-traceback/) - Reading tracebacks, file identification
- [Choosing Between ruamel.yaml and PyYAML](https://www.oreateai.com/blog/choosing-between-ruamelyaml-and-pyyaml-a-comprehensive-comparison/2ca85e856751622588a46a00a9a8e664) - YAML library comparison
- [GitHub REST API endpoints for issue comments](https://docs.github.com/en/rest/issues/comments) - Issue comment API
- [GitHub REST API endpoints for pull requests](https://docs.github.com/en/rest/pulls/pulls) - Pull request API
- [Mastering Retries in Python with the Tenacity Library](https://pub.towardsai.net/mastering-retries-in-python-with-the-tenacity-library-873f22ef64b3) - Tenacity usage patterns

### Tertiary (LOW confidence)

- [Using Python AST to resolve dependencies](https://gauravsarma1992.medium.com/using-python-ast-to-resolve-dependencies-c849bd184020) - AST-based import analysis (complex, may not be needed)
- [junitparser documentation](https://junitparser.readthedocs.io/) - Alternative: structured XML parsing (if we need machine-readable test results)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All recommendations based on official docs and existing project dependencies
- Architecture: HIGH - Patterns verified from official Python and library documentation
- Pitfalls: MEDIUM-HIGH - Combination of documentation warnings and general async Python best practices

**Research date:** 2026-02-14
**Valid until:** ~60 days (stable technologies, Python stdlib and mature libraries)
