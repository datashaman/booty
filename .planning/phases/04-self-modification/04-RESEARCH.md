# Phase 4: Self-Modification - Research

**Researched:** 2026-02-14
**Domain:** Self-referential system safety, URL normalization, per-repo configuration, GitHub PR enhancements, quality gate automation
**Confidence:** HIGH

## Summary

Self-modification requires detecting when Booty targets its own repository, enforcing safety boundaries through configurable protected paths, requiring human approval for all self-PRs, and validating the system through graduated integration tests. The phase builds on existing PathRestrictor patterns (from Phase 2) and extends them with per-repo configuration loaded from `.booty.yml`.

The standard approach uses `giturlparse` for normalizing GitHub URLs across HTTPS/SSH variants, extends existing PyYAML + Pydantic patterns for `.booty.yml` schema validation with new `protected_paths` field, leverages PyGithub's native support for draft PRs, labels, and review requests, and uses `ruff` for linting/formatting checks as stricter quality gates. Integration testing follows FastAPI's `httpx.AsyncClient` patterns for simulating webhook events end-to-end.

**Primary recommendation:** Use giturlparse for URL comparison, extend existing BootyConfig Pydantic model with protected_paths field, use PyGithub's `create_review_request()` and `add_to_labels()` for human approval flow, add ruff format --check and ruff check to test pipeline for self-PRs, and write integration tests using httpx.AsyncClient to POST mock webhook payloads.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| giturlparse | 0.12+ | Git URL parsing and normalization | De facto standard for normalizing GitHub URLs, handles HTTPS/SSH/git protocol variants, extracts owner/repo consistently |
| PyYAML | 6.0+ (already in project) | YAML parsing for .booty.yml | Already used in Phase 3, simple and sufficient for config file parsing |
| pydantic | 2.x (already in project) | Config schema validation | Already used throughout project, extend existing BootyConfig model with protected_paths |
| PyGithub | 2.x (already in project) | GitHub API interactions | Already used for PR creation, has native support for draft PRs, labels, and review requests |
| ruff | 0.15+ | Linting and formatting | Extremely fast (100x faster than Black), combines linter + formatter, Black-compatible, single tool replaces 10+ others |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathspec | 0.12+ (already in project) | Gitignore-style pattern matching | Already used in PathRestrictor, extend for protected_paths validation |
| httpx | 0.27+ (already in dev deps) | Async HTTP client for testing | Already in dev dependencies, use AsyncClient for integration tests |
| pytest-asyncio | 0.23+ (already in dev deps) | Async test support | Already in dev dependencies, mark integration tests with @pytest.mark.asyncio |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| giturlparse | Manual regex parsing | giturlparse handles edge cases (port numbers, authentication tokens, subgroups) that manual parsing misses |
| ruff | black + flake8 + isort | ruff is 30-100x faster and provides single unified interface, Black alone doesn't include linting |
| PyGithub review requests | Manual GraphQL API | PyGithub abstracts GraphQL complexity, handles authentication and retries |
| URL string comparison | urllib.parse.urlparse | urllib doesn't normalize git@ SSH format, doesn't extract owner/repo, giturlparse is purpose-built for Git URLs |

**Installation:**
```bash
pip install giturlparse ruff
```

## Architecture Patterns

### Recommended Project Structure
```
src/booty/
├── config.py              # Existing, extend Settings with BOOTY_OWN_REPO_URL, BOOTY_SELF_MODIFY_ENABLED, BOOTY_SELF_MODIFY_REVIEWER
├── webhooks.py            # Existing, add self-target detection before job creation
├── code_gen/
│   ├── security.py        # Existing PathRestrictor, extend with protected_paths from .booty.yml
│   ├── generator.py       # Existing, add quality gate logic (self-modification flag triggers ruff checks)
│   └── validator.py       # Existing, use for protected path validation
├── github/
│   ├── pulls.py           # Existing, extend create_pull_request with reviewer, label, safety summary
│   └── comments.py        # Existing, add comment for self-modification rejection when disabled
├── test_runner/
│   ├── config.py          # Existing BootyConfig, add protected_paths field
│   └── quality.py         # New: run ruff format --check and ruff check
└── self_modification/     # New module (optional organizational choice)
    ├── __init__.py
    ├── detector.py        # URL comparison logic
    └── safety.py          # Protected paths enforcement
```

### Pattern 1: Git URL Normalization and Comparison

**What:** Compare repository URLs robustly across different URL formats
**When to use:** Webhook handler to detect when incoming repo matches BOOTY_OWN_REPO_URL

**Example:**
```python
# Source: https://github.com/nephila/giturlparse
from giturlparse import parse, validate

def is_same_repository(url1: str, url2: str) -> bool:
    """Compare two Git URLs for repository equality.

    Handles:
    - HTTPS vs SSH: https://github.com/owner/repo vs git@github.com:owner/repo
    - Trailing .git: repo.git vs repo
    - Case differences: GitHub is case-insensitive for repos
    - URL variants: http vs https, with/without trailing slashes

    Args:
        url1: First repository URL
        url2: Second repository URL

    Returns:
        True if URLs refer to same repository, False otherwise
    """
    # Validate both URLs
    if not validate(url1) or not validate(url2):
        return False

    p1 = parse(url1)
    p2 = parse(url2)

    # Compare normalized components (case-insensitive)
    return (
        p1.host.lower() == p2.host.lower()
        and p1.owner.lower() == p2.owner.lower()
        and p1.repo.lower() == p2.repo.lower()
    )
```

### Pattern 2: Protected Paths in .booty.yml Configuration

**What:** Per-repo configuration of paths that cannot be modified by LLM
**When to use:** Load during workspace preparation, validate before applying changes

**Example:**
```python
# Source: Extending Phase 3 pattern from https://medium.com/better-programming/validating-yaml-configs-made-easy-with-pydantic-594522612db5
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
import yaml

class BootyConfig(BaseModel):
    """Schema for .booty.yml configuration file."""

    # Phase 3 fields
    test_command: str = Field(..., description="Shell command to run tests")
    timeout: int = Field(default=300, ge=10, le=3600)
    max_retries: int = Field(default=3, ge=1, le=10)

    # Phase 4: Self-modification safety
    protected_paths: list[str] = Field(
        default_factory=lambda: [
            ".github/workflows/**",
            ".env",
            ".env.*",
            "**/*.env",
            "**/secrets.*",
            "Dockerfile",
            "docker-compose*.yml",
        ],
        description="Gitignore-style patterns for paths that cannot be modified",
    )

    @field_validator('protected_paths')
    @classmethod
    def validate_protected_paths_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure at least basic protections exist."""
        if not v:
            # Enforce minimum safety: always protect workflows and secrets
            return [".github/workflows/**", ".env", ".env.*"]
        return v

def load_booty_config(workspace_path: Path) -> BootyConfig:
    """Load and validate .booty.yml from workspace root.

    For repos without .booty.yml, returns default config with protected_paths
    but raises FileNotFoundError if test_command is needed (Phase 3).

    For self-modification repos, .booty.yml should exist and specify
    protected_paths to prevent accidental core file modification.
    """
    config_path = workspace_path / ".booty.yml"

    if not config_path.exists():
        # Return defaults for protected_paths (Phase 4 can work without .booty.yml)
        # But Phase 3 test-driven refinement requires test_command
        return BootyConfig(test_command="echo 'No tests configured'")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    return BootyConfig.model_validate(data)
```

### Pattern 3: Draft PR with Label and Reviewer

**What:** Create PR with draft status, self-modification label, and auto-requested reviewer
**When to use:** All self-modification PRs regardless of test results

**Example:**
```python
# Source: https://pygithub.readthedocs.io/en/latest/github_objects/PullRequest.html
from github import Auth, Github
from urllib.parse import urlparse

def create_self_modification_pr(
    github_token: str,
    repo_url: str,
    head_branch: str,
    base_branch: str,
    title: str,
    body: str,
    reviewer_username: str,
    changed_files: list[str],
) -> int:
    """Create draft PR for self-modification with safety annotations.

    Args:
        github_token: GitHub authentication token
        repo_url: Repository URL
        head_branch: Source branch name
        base_branch: Target branch name
        title: PR title
        body: PR body (should include safety summary)
        reviewer_username: GitHub username to request review from
        changed_files: List of files modified (for safety summary)

    Returns:
        PR number
    """
    # Parse owner/repo from URL
    parsed = urlparse(repo_url)
    path = parsed.path.lstrip('/').removesuffix('.git')

    auth = Auth.Token(github_token)
    g = Github(auth=auth)
    repo = g.get_repo(path)

    # Create PR as draft
    pr = repo.create_pull(
        title=title,
        body=body,
        head=head_branch,
        base=base_branch,
        draft=True,  # Always draft for self-modification
    )

    # Add self-modification label
    pr.add_to_labels("self-modification")

    # Request reviewer
    pr.create_review_request(reviewers=[reviewer_username])

    return pr.number


def format_self_modification_pr_body(
    approach: str,
    file_changes: list[dict],
    testing_notes: str,
    issue_number: int,
    protected_paths_checked: list[str],
    changed_files: list[str],
) -> str:
    """Format PR body with self-modification safety summary.

    Args:
        approach: Summary of approach taken
        file_changes: List of dicts with keys: path, operation, explanation
        testing_notes: Testing instructions
        issue_number: GitHub issue number
        protected_paths_checked: Patterns that were verified
        changed_files: Actual files modified

    Returns:
        Formatted PR body markdown with safety summary
    """
    # Build changes table
    table_rows = []
    for change in file_changes:
        path = change["path"]
        operation = change["operation"]
        explanation = change["explanation"]
        table_rows.append(f"| {path} | {operation} | {explanation} |")

    changes_table = "\n".join(table_rows)

    # Safety summary
    safety_summary = f"""## 🔒 Self-Modification Safety Summary

**This PR modifies Booty's own repository.**

**Files changed:** {len(changed_files)}
- {chr(10).join(f'- `{f}`' for f in changed_files[:10])}
{f'- ... and {len(changed_files) - 10} more' if len(changed_files) > 10 else ''}

**Protected paths verified:**
- {chr(10).join(f'- `{p}`' for p in protected_paths_checked[:5])}
{f'- ... and {len(protected_paths_checked) - 5} more patterns' if len(protected_paths_checked) > 5 else ''}

**✅ No protected paths were modified.**

---
"""

    # Format body
    body = f"""{safety_summary}
## Summary
{approach}

## Changes
| File | Operation | Description |
|------|-----------|-------------|
{changes_table}

## Testing
{testing_notes}

---
Fixes #{issue_number}
Generated by [Booty](https://github.com/datashaman/booty) (self-modification)"""

    return body
```

### Pattern 4: Ruff Quality Checks for Self-PRs

**What:** Run both formatting and linting checks before creating PR
**When to use:** Self-modification PRs only (stricter quality gate than external repos)

**Example:**
```python
# Source: https://docs.astral.sh/ruff/formatter/
import asyncio
from pathlib import Path
from dataclasses import dataclass

@dataclass
class QualityCheckResult:
    """Result of quality checks."""
    passed: bool
    formatting_ok: bool
    linting_ok: bool
    errors: list[str]

async def run_quality_checks(workspace_path: Path) -> QualityCheckResult:
    """Run ruff format check and ruff check on workspace.

    Args:
        workspace_path: Path to workspace root

    Returns:
        QualityCheckResult with pass/fail status and error details
    """
    errors = []

    # Check 1: Formatting (ruff format --check)
    proc = await asyncio.create_subprocess_shell(
        "ruff format --check .",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(workspace_path),
    )
    stdout, stderr = await proc.communicate()
    formatting_ok = proc.returncode == 0

    if not formatting_ok:
        errors.append(f"Formatting check failed:\n{stderr.decode()}")

    # Check 2: Linting (ruff check)
    proc = await asyncio.create_subprocess_shell(
        "ruff check .",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(workspace_path),
    )
    stdout, stderr = await proc.communicate()
    linting_ok = proc.returncode == 0

    if not linting_ok:
        errors.append(f"Linting check failed:\n{stdout.decode()}")

    return QualityCheckResult(
        passed=formatting_ok and linting_ok,
        formatting_ok=formatting_ok,
        linting_ok=linting_ok,
        errors=errors,
    )
```

### Pattern 5: Integration Test with Mock Webhook

**What:** End-to-end test that simulates webhook event for self-modification
**When to use:** Bootstrap validation and regression testing

**Example:**
```python
# Source: https://fastapi.tiangolo.com/advanced/async-tests/
import pytest
from httpx import ASGITransport, AsyncClient
from booty.main import app
import json
import hmac
import hashlib

@pytest.mark.asyncio
async def test_self_modification_webhook_disabled_by_default():
    """Test that self-modification is rejected when BOOTY_SELF_MODIFY_ENABLED=false."""
    # Mock webhook payload for Booty's own repo
    payload = {
        "action": "labeled",
        "label": {"name": "agent:builder"},
        "issue": {
            "number": 123,
            "html_url": "https://github.com/datashaman/booty/issues/123",
        },
        "repository": {
            "html_url": "https://github.com/datashaman/booty",
        },
    }

    payload_bytes = json.dumps(payload).encode()

    # Compute HMAC signature
    secret = "test-secret"
    signature = "sha256=" + hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/webhooks/github",
            content=payload_bytes,
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Delivery": "test-delivery-1",
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )

    # Should be rejected (not enqueued)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"

    # TODO: Verify issue comment was posted explaining self-modification is disabled

@pytest.mark.asyncio
async def test_self_modification_creates_draft_pr_with_reviewer():
    """Test that self-modification PR is created as draft with reviewer requested."""
    # This test requires mocking:
    # 1. Self-modification detection (BOOTY_OWN_REPO_URL matches webhook repo)
    # 2. GitHub API calls (PyGithub)
    # 3. LLM calls (Magentic/Anthropic)

    # Integration test structure (simplified):
    # - Set BOOTY_SELF_MODIFY_ENABLED=true
    # - Set BOOTY_OWN_REPO_URL to match webhook payload
    # - Send webhook with self-repo URL
    # - Mock LLM to return simple code change
    # - Verify PR created with draft=True, label="self-modification", reviewer requested

    # TODO: Implement with pytest-mock or unittest.mock
    pass
```

### Anti-Patterns to Avoid

- **String comparison for URLs:** Don't use `url1 == url2` - misses SSH vs HTTPS equivalence, trailing .git differences, case variations
- **Global protected paths list:** Don't hardcode protected paths in Booty - each repo has different critical files, make it configurable per-repo
- **Self-modification always allowed:** Don't enable by default - requires explicit opt-in to prevent accidental self-modification
- **Same quality gates for self vs external:** Don't skip linting/formatting for self-PRs - they should have STRICTER gates, not looser
- **Auto-merge self-PRs:** Don't allow self-modification PRs to merge without human review - defeats the purpose of safety rails
- **URL comparison without normalization:** Don't compare raw URL strings - GitHub URLs have many equivalent forms that won't match with ==

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Git URL parsing | Regex for extracting owner/repo | `giturlparse` library | Handles SSH format, authentication tokens, port numbers, .git suffix, groups/subgroups |
| URL normalization | Manual string manipulation | `giturlparse.parse()` with component comparison | Covers HTTPS/SSH/git protocol variants, case-insensitive comparison, port normalization |
| Linting + formatting | Separate tools (black, flake8, isort, etc.) | `ruff` (all-in-one) | 30-100x faster, single config file, consistent behavior, Black-compatible formatting |
| Protected path matching | Custom path matching logic | Extend existing `PathRestrictor` with `pathspec` | Already handles gitignore patterns, path traversal prevention, workspace boundaries |
| Draft PR creation | Manual GitHub GraphQL | PyGithub `create_pull(draft=True)` | Abstracts GraphQL complexity, handles authentication, provides type-safe API |
| PR review requests | Manual REST API calls | PyGithub `pr.create_review_request()` | Handles user vs team reviewers, validates reviewer existence, retries on failure |

**Key insight:** Self-modification safety requires robust URL comparison and path protection. Git URLs have many equivalent representations (HTTPS/SSH, with/without .git, case variations) that simple string comparison misses. Use giturlparse for reliable detection. Similarly, path protection needs gitignore-style pattern matching with workspace boundary enforcement - extend existing PathRestrictor rather than building new logic.

## Common Pitfalls

### Pitfall 1: False Positive Self-Detection from Forks

**What goes wrong:** Webhook for a fork of Booty incorrectly matches BOOTY_OWN_REPO_URL because only repo name is compared, not owner.

**Why it happens:** Comparing only `p.repo` instead of `p.owner` + `p.repo` combination.

**How to avoid:**
```python
# BAD: Only compares repo name
return p1.repo.lower() == p2.repo.lower()

# GOOD: Compares owner AND repo
return (
    p1.host.lower() == p2.host.lower()
    and p1.owner.lower() == p2.owner.lower()
    and p1.repo.lower() == p2.repo.lower()
)
```

**Warning signs:** Self-modification logic triggered for repos named "booty" but owned by different users

### Pitfall 2: Protected Paths Checked After File Write

**What goes wrong:** Files are written to workspace before checking protected paths, leaving filesystem in inconsistent state when validation fails.

**Why it happens:** Validation happens in wrong order - apply changes first, validate second.

**How to avoid:** Validate ALL paths before writing ANY files:
```python
# GOOD: Validate before applying
def apply_changes_to_workspace(workspace_path: Path, changes: list[FileChange], restrictor: PathRestrictor):
    # Step 1: Validate all paths first
    restrictor.validate_all_paths([c.path for c in changes])

    # Step 2: Only if validation passes, write files
    for change in changes:
        write_file(workspace_path / change.path, change.content)
```

**Warning signs:** Partial file writes in workspace when protected path error occurs, need for rollback/cleanup logic

### Pitfall 3: Self-Modification Label Not Created

**What goes wrong:** Label "self-modification" doesn't exist in repo, `pr.add_to_labels()` fails silently or raises exception.

**Why it happens:** Assuming label exists without checking or creating it first.

**How to avoid:** Create label if it doesn't exist, or catch exception:
```python
# Option 1: Try/except pattern (simpler)
try:
    pr.add_to_labels("self-modification")
except GithubException as e:
    if e.status == 404:
        # Label doesn't exist - create it
        repo.create_label("self-modification", "ff6b6b", "Self-modification PR requiring manual review")
        pr.add_to_labels("self-modification")
    else:
        raise

# Option 2: Check and create upfront (cleaner)
def ensure_self_modification_label_exists(repo):
    """Ensure self-modification label exists in repository."""
    try:
        repo.get_label("self-modification")
    except GithubException as e:
        if e.status == 404:
            repo.create_label("self-modification", "ff6b6b", "Self-modification PR requiring manual review")
        else:
            raise
```

**Warning signs:** PR created without label, exception in PR creation logs, missing visual indicator in GitHub UI

### Pitfall 4: Ruff Not Installed in Target Repo

**What goes wrong:** Self-modification quality check fails because target repo (Booty) doesn't have ruff installed or configured.

**Why it happens:** Assuming quality tools are available without checking, or running in wrong environment.

**How to avoid:** Check for ruff availability, or install as part of workspace preparation:
```python
async def run_quality_checks(workspace_path: Path) -> QualityCheckResult:
    """Run ruff checks if available, skip gracefully if not installed."""
    # Check if ruff is available
    proc = await asyncio.create_subprocess_shell(
        "which ruff",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.wait()

    if proc.returncode != 0:
        # Ruff not installed - skip quality checks with warning
        logger.warning("ruff_not_found", message="Skipping quality checks, ruff not installed")
        return QualityCheckResult(passed=True, formatting_ok=True, linting_ok=True, errors=[])

    # Ruff available - run checks
    # ... (run ruff format --check and ruff check)
```

**Warning signs:** Command not found errors, quality checks always skipped, inconsistent enforcement

### Pitfall 5: Reviewer Username Doesn't Exist

**What goes wrong:** `pr.create_review_request(reviewers=[username])` fails because configured username is invalid or has wrong permissions.

**Why it happens:** Typo in BOOTY_SELF_MODIFY_REVIEWER env var, or user doesn't have repo access.

**How to avoid:** Validate reviewer on startup or handle gracefully:
```python
# Option 1: Validate on startup
async def validate_config_on_startup(settings: Settings):
    """Validate configuration when app starts."""
    if settings.BOOTY_SELF_MODIFY_ENABLED and settings.BOOTY_SELF_MODIFY_REVIEWER:
        # Verify user exists and has access
        g = Github(auth=Auth.Token(settings.GITHUB_TOKEN))
        try:
            user = g.get_user(settings.BOOTY_SELF_MODIFY_REVIEWER)
            logger.info("reviewer_validated", username=user.login)
        except GithubException as e:
            logger.error("invalid_reviewer", username=settings.BOOTY_SELF_MODIFY_REVIEWER, error=str(e))
            raise ValueError(f"Invalid BOOTY_SELF_MODIFY_REVIEWER: {settings.BOOTY_SELF_MODIFY_REVIEWER}")

# Option 2: Graceful degradation (create PR without reviewer if request fails)
try:
    pr.create_review_request(reviewers=[reviewer_username])
except GithubException as e:
    logger.warning("review_request_failed", username=reviewer_username, error=str(e))
    # PR still created, just without auto-requested reviewer
```

**Warning signs:** PR created without reviewer, GitHub API errors in logs, review requests silently failing

### Pitfall 6: Missing Self-Modification Comment on Rejection

**What goes wrong:** When self-modification is detected but disabled, job is ignored without explaining WHY to the user who labeled the issue.

**Why it happens:** Early return from webhook handler without posting explanatory comment.

**How to avoid:** Post issue comment before returning when self-modification is rejected:
```python
# In webhook handler, after detecting self-modification
if is_self_modification and not settings.BOOTY_SELF_MODIFY_ENABLED:
    logger.info("self_modification_rejected", issue_number=issue["number"])

    # Post explanatory comment
    post_issue_comment(
        settings.GITHUB_TOKEN,
        settings.TARGET_REPO_URL,
        issue["number"],
        "❌ **Self-modification disabled**\n\n"
        "This issue was labeled for processing, but self-modification is not enabled. "
        "Set `BOOTY_SELF_MODIFY_ENABLED=true` to allow Booty to process issues against its own repository.\n\n"
        "For safety, self-modification requires explicit opt-in and will always create draft PRs requiring human review."
    )

    return {"status": "ignored", "reason": "self_modification_disabled"}
```

**Warning signs:** Users confused why labeled issues aren't processing, no feedback on self-modification attempts, silent failures

## Code Examples

### Complete Self-Modification Detection Module

```python
# src/booty/self_modification/detector.py
"""Self-modification detection via URL comparison."""
from giturlparse import parse, validate
from booty.logging import get_logger

logger = get_logger()


def is_self_modification(webhook_repo_url: str, booty_own_repo_url: str) -> bool:
    """Detect if webhook targets Booty's own repository.

    Compares URLs robustly across HTTPS/SSH variants, .git suffixes, case differences.

    Args:
        webhook_repo_url: Repository URL from webhook payload (repository.html_url)
        booty_own_repo_url: Configured Booty repository URL (BOOTY_OWN_REPO_URL env var)

    Returns:
        True if webhook targets Booty itself, False otherwise

    Examples:
        >>> is_self_modification(
        ...     "https://github.com/datashaman/booty",
        ...     "git@github.com:datashaman/booty.git"
        ... )
        True

        >>> is_self_modification(
        ...     "https://github.com/otheruser/booty",
        ...     "https://github.com/datashaman/booty"
        ... )
        False
    """
    # Validate both URLs
    if not validate(webhook_repo_url):
        logger.warning("invalid_webhook_url", url=webhook_repo_url)
        return False

    if not validate(booty_own_repo_url):
        logger.error("invalid_booty_own_url", url=booty_own_repo_url)
        return False

    # Parse URLs
    p_webhook = parse(webhook_repo_url)
    p_booty = parse(booty_own_repo_url)

    # Compare normalized components (case-insensitive for GitHub)
    is_same = (
        p_webhook.host.lower() == p_booty.host.lower()
        and p_webhook.owner.lower() == p_booty.owner.lower()
        and p_webhook.repo.lower() == p_booty.repo.lower()
    )

    logger.info(
        "self_modification_check",
        is_self=is_same,
        webhook_repo=f"{p_webhook.owner}/{p_webhook.repo}",
        booty_repo=f"{p_booty.owner}/{p_booty.repo}",
    )

    return is_same
```

### Protected Paths Validation with .booty.yml

```python
# src/booty/self_modification/safety.py
"""Protected paths enforcement for self-modification."""
from pathlib import Path
from booty.code_gen.security import PathRestrictor
from booty.test_runner.config import load_booty_config
from booty.logging import get_logger

logger = get_logger()


def create_self_modification_restrictor(workspace_path: Path) -> PathRestrictor:
    """Create PathRestrictor with protected_paths from .booty.yml.

    For self-modification, protected_paths define additional restrictions
    beyond RESTRICTED_PATHS from Settings.

    Args:
        workspace_path: Path to workspace root (should contain .booty.yml)

    Returns:
        PathRestrictor configured with protected_paths patterns

    Raises:
        FileNotFoundError: If .booty.yml doesn't exist (required for self-modification)
        ValidationError: If .booty.yml is invalid
    """
    # Load .booty.yml (raises if missing)
    config = load_booty_config(workspace_path)

    logger.info(
        "protected_paths_loaded",
        count=len(config.protected_paths),
        patterns=config.protected_paths[:5],  # Log first 5 patterns
    )

    # Create restrictor with protected_paths
    # Note: This replaces RESTRICTED_PATHS from Settings for self-modification
    # because each repo defines its own critical paths
    return PathRestrictor(
        workspace_root=workspace_path,
        denylist_patterns=config.protected_paths,
    )


def validate_changes_against_protected_paths(
    changes: list[dict],
    workspace_path: Path,
) -> tuple[bool, str | None]:
    """Validate that changes don't touch protected paths.

    Args:
        changes: List of FileChange-like dicts with 'path' key
        workspace_path: Path to workspace root

    Returns:
        (allowed, reason) tuple
        - (True, None) if all changes allowed
        - (False, reason) if any change violates protected paths
    """
    try:
        restrictor = create_self_modification_restrictor(workspace_path)
    except FileNotFoundError:
        return False, "Self-modification requires .booty.yml with protected_paths configuration"

    # Validate each path
    for change in changes:
        path = change["path"]
        allowed, reason = restrictor.is_path_allowed(path)

        if not allowed:
            logger.warning("protected_path_violation", path=path, reason=reason)
            return False, f"Protected path violation: {reason}"

    logger.info("protected_paths_validated", changed_files=len(changes))
    return True, None
```

### Quality Gate Runner

```python
# src/booty/test_runner/quality.py
"""Quality checks (linting and formatting) for self-modification."""
import asyncio
from pathlib import Path
from dataclasses import dataclass
from booty.logging import get_logger

logger = get_logger()


@dataclass
class QualityCheckResult:
    """Result of quality checks (linting + formatting)."""
    passed: bool
    formatting_ok: bool
    linting_ok: bool
    errors: list[str]


async def run_quality_checks(workspace_path: Path) -> QualityCheckResult:
    """Run ruff format --check and ruff check.

    Args:
        workspace_path: Path to workspace root

    Returns:
        QualityCheckResult with pass/fail status and errors
    """
    logger.info("running_quality_checks", workspace=str(workspace_path))

    errors = []

    # Check 1: Formatting
    logger.info("checking_formatting")
    proc = await asyncio.create_subprocess_shell(
        "ruff format --check .",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(workspace_path),
    )
    stdout, stderr = await proc.communicate()
    formatting_ok = proc.returncode == 0

    if not formatting_ok:
        error_msg = stderr.decode() or stdout.decode()
        logger.warning("formatting_check_failed", output=error_msg[:200])
        errors.append(f"Formatting check failed:\n{error_msg}")

    # Check 2: Linting
    logger.info("checking_linting")
    proc = await asyncio.create_subprocess_shell(
        "ruff check .",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(workspace_path),
    )
    stdout, stderr = await proc.communicate()
    linting_ok = proc.returncode == 0

    if not linting_ok:
        error_msg = stdout.decode() or stderr.decode()
        logger.warning("linting_check_failed", output=error_msg[:200])
        errors.append(f"Linting check failed:\n{error_msg}")

    passed = formatting_ok and linting_ok

    logger.info(
        "quality_checks_complete",
        passed=passed,
        formatting_ok=formatting_ok,
        linting_ok=linting_ok,
    )

    return QualityCheckResult(
        passed=passed,
        formatting_ok=formatting_ok,
        linting_ok=linting_ok,
        errors=errors,
    )
```

### Extended Settings with Self-Modification Config

```python
# src/booty/config.py (additions to existing Settings class)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ... existing fields ...

    # Phase 4: Self-modification configuration
    BOOTY_OWN_REPO_URL: str = ""  # Empty means self-modification disabled
    BOOTY_SELF_MODIFY_ENABLED: bool = False  # Explicit opt-in
    BOOTY_SELF_MODIFY_REVIEWER: str = ""  # GitHub username for review requests

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual URL parsing with regex | giturlparse library | 2015 (giturlparse 0.1.0) | Reliable parsing of SSH/HTTPS/git formats, handles edge cases |
| Black + Flake8 + isort + pyupgrade + ... | ruff (all-in-one) | 2023 (ruff 0.1.0) | 30-100x faster, single config, 10+ tools replaced |
| Manual GraphQL for draft PRs | PyGithub with draft support | 2019 (PyGithub 1.44) | Simplified API, abstracts GraphQL complexity |
| String comparison for URLs | Normalized component comparison | N/A | Robust handling of HTTPS/SSH, .git suffix, case variations |
| Global path restrictions | Per-repo .booty.yml protected_paths | N/A (Phase 4 design) | Each repo defines its own critical files, reusable beyond Booty |

**Deprecated/outdated:**
- Manual URL regex: Use giturlparse for Git URL parsing
- Running black, isort, flake8 separately: Use ruff for unified linting and formatting
- String equality for URL comparison: Use giturlparse normalization with component comparison
- Hardcoded protected paths: Use per-repo .booty.yml configuration

## Open Questions

1. **Should quality checks apply to external repos too?**
   - What we know: Self-modification PRs run ruff checks, external repos don't
   - What's unclear: Would external repos benefit from same quality gates?
   - Recommendation: Start with self-modification only (stricter for self, don't impose on others). Can make it opt-in via .booty.yml in Phase 5 if useful.

2. **How to handle self-modification when .booty.yml doesn't exist?**
   - What we know: Protected paths come from .booty.yml
   - What's unclear: Should we fall back to defaults or reject self-modification?
   - Recommendation: Reject with clear error - require .booty.yml for self-modification to ensure protected_paths are explicitly configured (fail-safe approach).

3. **Should ruff configuration come from target repo's pyproject.toml?**
   - What we know: Ruff reads config from pyproject.toml if present
   - What's unclear: Do we run ruff with target repo's config or force Booty's standards?
   - Recommendation: Use target repo's config (respect their standards). Ruff automatically discovers pyproject.toml in workspace.

4. **What if reviewer username is a team, not a user?**
   - What we know: PyGithub supports team_reviewers parameter separately
   - What's unclear: Should BOOTY_SELF_MODIFY_REVIEWER support both formats?
   - Recommendation: Start with username only (simpler). Can add team support in v2 if needed - format could be "username" vs "org/team" to distinguish.

5. **Should bootstrap tests run in CI or locally?**
   - What we know: Need automated validation that self-modification works
   - What's unclear: Run in GitHub Actions or as manual local test?
   - Recommendation: Both - local pytest for development, CI for regression prevention. Use real GitHub API in CI (integration test), mock in local pytest (unit test).

## Sources

### Primary (HIGH confidence)

- [giturlparse PyPI](https://pypi.org/project/giturlparse/) - Git URL parsing library capabilities
- [giturlparse GitHub](https://github.com/nephila/giturlparse) - Usage examples, supported formats, normalization methods
- [PyGithub PullRequest documentation](https://pygithub.readthedocs.io/en/latest/github_objects/PullRequest.html) - Draft PR, labels, review requests
- [Ruff Formatter documentation](https://docs.astral.sh/ruff/formatter/) - Format checking, exit codes, configuration
- [Ruff pre-commit GitHub](https://github.com/astral-sh/ruff-pre-commit) - Hook IDs, recommended settings
- [FastAPI async tests documentation](https://fastapi.tiangolo.com/advanced/async-tests/) - httpx.AsyncClient, ASGITransport patterns
- [PathSpec API documentation](https://python-path-specification.readthedocs.io/en/latest/api.html) - PathSpec vs GitIgnoreSpec, match_file usage

### Secondary (MEDIUM confidence)

- [How to Validate YAML Configs Using Pydantic](https://medium.com/better-programming/validating-yaml-configs-made-easy-with-pydantic-594522612db5) - PyYAML + Pydantic pattern
- [Ruff: An extremely fast Python linter](https://github.com/astral-sh/ruff) - Performance benchmarks, Black compatibility
- [Modern Python Code Quality Setup](https://simone-carolini.medium.com/modern-python-code-quality-setup-uv-ruff-and-mypy-8038c6549dcc) - Ruff integration patterns
- [URI normalization - Wikipedia](https://en.wikipedia.org/wiki/URI_normalization) - RFC 3986 standards for URL comparison
- [Developing and Testing an Asynchronous API with FastAPI and Pytest](https://testdriven.io/blog/fastapi-crud/) - FastAPI async testing patterns

### Tertiary (LOW confidence)

- [PyGithub Issues #1244](https://github.com/PyGithub/PyGithub/issues/1244) - Discussion on PR labels (not authoritative)
- [pytest-httpx PyPI](https://pypi.org/project/pytest-httpx/) - HTTP mocking for httpx (may be useful but not verified for this use case)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All recommendations based on official docs and existing project patterns
- Architecture: HIGH - Extends proven patterns from Phase 2 (PathRestrictor) and Phase 3 (BootyConfig)
- Pitfalls: MEDIUM-HIGH - Combination of official docs and anticipated edge cases from URL/path handling

**Research date:** 2026-02-14
**Valid until:** ~90 days (stable technologies, mostly extending existing patterns)
