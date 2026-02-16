# Booty - GitHub Copilot Instructions

## Project Overview

Booty is a self-managing software builder powered by AI. It receives GitHub issues via webhook, analyzes them with an LLM, generates code changes, runs tests with iterative refinement, and opens pull requests — including against its own repository with additional safety gates.

**Core Value**: A Builder agent that can take a GitHub issue and produce a working PR with tested code.

## Agents and Components

Booty is a multi-agent system with the following components:

### Builder Agent (code_gen/)
- **Trigger**: GitHub issues with `agent` label
- **Function**: Analyzes issue → generates code → runs tests → iterative refinement → opens PR
- **Key modules**: generator.py, refiner.py, validator.py
- **Safety**: Self-modification gates, path restrictions, token budget management
- **Output**: Pull request with tested code changes

### Verifier Agent (verifier/)
- **Trigger**: `pull_request` webhook (opened, synchronize, reopened)
- **Function**: Posts `booty/verifier` check run with limits validation, import/compile detection
- **Key modules**: runner.py, limits.py, imports.py
- **Validation**: Max files changed, max diff LOC, .booty.yml schema, import errors
- **Output**: GitHub check run (success/failure with annotations)

### Security Agent (security/)
- **Trigger**: `pull_request` webhook (parallel with Verifier)
- **Function**: Posts `booty/security` check run with secret scan, dependency audit, permission drift
- **Key modules**: runner.py, scanner.py, audit.py, permission_drift.py
- **Decision model**: PASS, FAIL (secrets/vulns), ESCALATE (sensitive paths)
- **Integration**: ESCALATE persists override for Release Governor to use HIGH risk
- **Output**: GitHub check run with annotations or escalation notice

### Release Governor (release_governor/)
- **Trigger**: `workflow_run` completion on main (verification success)
- **Function**: Computes risk from diff vs production → applies decision rules → ALLOW/HOLD deploy
- **Key modules**: handler.py, decision.py, risk.py, deploy.py
- **Risk classes**: LOW (auto-allow), MEDIUM (allow unless degraded), HIGH (hold unless approved)
- **Output**: workflow_dispatch trigger (ALLOW) or commit status with hold reason

### Memory System (memory/)
- **Trigger**: Events from Observability, Governor, Security, Verifier, revert detection
- **Function**: Stores incidents, governor holds, failures, reverts → surfaces related history in PR comments
- **Key modules**: api.py, store.py, lookup.py, surfacing.py
- **Storage**: JSONL in state dir (~/.booty/state/memory.jsonl)
- **Retention**: 90 days default, surfaces up to 3 matches
- **Output**: "Related history" comments on PRs and incident issues

### Observability (github/issues.py)
- **Trigger**: Sentry webhook with filtered alerts
- **Function**: Auto-creates GitHub issues with `agent` label
- **Integration**: Sentry → filtered alerts → GitHub issue → Builder enqueues
- **Output**: GitHub issue ready for Builder agent

### Test Generation (test_generation/)
- **Trigger**: Called by Builder during code generation
- **Function**: Detects test conventions (language, framework, patterns) and validates test imports
- **Key modules**: detector.py, validator.py
- **Support**: Python, JavaScript, TypeScript, Go, Rust, PHP, Ruby, Java
- **Output**: DetectedConventions model for Builder to use

## Tech Stack

### Core Framework
- **Language**: Python 3.11+
- **Web Framework**: FastAPI with Uvicorn
- **Async**: asyncio for all I/O operations

### Key Dependencies
- **LLM Integration**: magentic[anthropic] - Decorator-based LLM abstraction
- **GitHub API**: PyGithub - GitHub REST API client
- **Git Operations**: GitPython - Git repository manipulation
- **Configuration**: pydantic-settings - Type-safe environment variables
- **Logging**: structlog - Structured logging with context
- **Correlation**: asgi-correlation-id - Request correlation tracking

### Development Tools
- **Testing**: pytest with pytest-asyncio
- **HTTP Client**: httpx for async HTTP requests

## Project Structure

```
src/booty/
├── __init__.py
├── main.py              # FastAPI app entrypoint, webhook receiver
├── cli.py               # CLI commands (status, verifier, governor, memory)
├── config.py            # Pydantic Settings for environment config
├── jobs.py              # Job queue and worker management
├── logging.py           # Structured logging configuration
├── repositories.py      # Workspace preparation and Git cloning
├── webhooks.py          # GitHub webhook signature verification
├── code_gen/            # Code generation and refinement (Builder agent)
│   ├── generator.py     # Main issue-to-PR pipeline orchestrator
│   ├── refiner.py       # Test-driven code refinement loop
│   ├── security.py      # Path restrictions and safety checks
│   └── validator.py     # Generated code validation
├── verifier/            # Verifier agent (PR checks)
│   ├── job.py           # Verifier job definition
│   ├── runner.py        # Verification pipeline
│   ├── limits.py        # Diff/file limits validation
│   ├── imports.py       # Import/compile detection
│   └── workspace.py     # Workspace setup for verification
├── security/            # Security agent (secrets, dependencies, permissions)
│   ├── job.py           # Security job definition
│   ├── runner.py        # Security scan pipeline
│   ├── scanner.py       # Secret scanning (gitleaks)
│   ├── audit.py         # Dependency vulnerability audit
│   └── permission_drift.py  # Sensitive path detection
├── release_governor/    # Release Governor (deployment gating)
│   ├── handler.py       # workflow_run pipeline
│   ├── decision.py      # Decision computation (ALLOW/HOLD)
│   ├── risk.py          # Risk classification (LOW/MEDIUM/HIGH)
│   ├── deploy.py        # Deploy trigger via workflow_dispatch
│   └── store.py         # Release state persistence
├── memory/              # Memory system (incident tracking)
│   ├── api.py           # add_record for agents
│   ├── store.py         # JSONL storage
│   ├── lookup.py        # Query by PR/SHA
│   └── surfacing.py     # Comment generation
├── test_generation/     # Test generation support
│   ├── detector.py      # Convention detection (language, framework)
│   ├── models.py        # DetectedConventions model
│   └── validator.py     # Test import validation
├── llm/                 # LLM interaction layer
│   ├── prompts.py       # Magentic prompt functions
│   ├── models.py        # Pydantic models for LLM responses
│   └── token_budget.py  # Token counting and context management
├── git/                 # Git operations
│   └── operations.py    # Commit, push, branch operations
├── github/              # GitHub API operations
│   ├── comments.py      # Issue/PR comment posting
│   ├── pulls.py         # PR creation and management
│   ├── checks.py        # Check runs (Verifier, Security)
│   └── issues.py        # Issue creation (Observability)
├── self_modification/   # Self-modification safety
│   ├── detector.py      # Detect if target is self
│   └── safety.py        # Self-modification gates
└── test_runner/         # Test execution
    ├── executor.py      # Test execution with output capture
    ├── parser.py        # Test output parsing
    └── config.py        # Test runner configuration
```

## Coding Standards

### Python Style
- Use **type hints** for all function signatures and class attributes
- Use **async/await** for all I/O operations (no sync blocking calls)
- Use **dataclasses** for simple data containers
- Use **Pydantic models** for validation and serialization
- Use **f-strings** for string formatting
- Use **pathlib.Path** instead of os.path for file operations
- Use **| None** syntax instead of Optional (Python 3.10+)
- Use **list[T]** and **dict[K, V]** instead of List[T] and Dict[K, V]

### Code Organization
- Keep functions focused and single-purpose
- Extract complex logic into separate functions
- Use descriptive variable names (no abbreviations unless obvious)
- Group related functionality into modules
- Keep modules under 500 lines when possible

### Documentation
- Use docstrings for modules, classes, and functions
- Follow Google-style docstring format
- Include Args and Returns sections
- Skip docstrings for obvious property getters

### Error Handling
- Use structured logging for errors (logger.error with context)
- Don't catch broad exceptions unless re-raising with context
- Let FastAPI handle HTTP exceptions
- Use tenacity for retry logic where appropriate

### Testing
- Place tests in tests/ directory mirroring src/ structure
- Use pytest fixtures for common setup
- Use pytest-asyncio for async test support
- Mock external services (GitHub API, Git operations, LLM calls)
- Test happy paths and common error cases

## Configuration

### Environment Variables
All configuration is loaded through `config.py` using Pydantic Settings:

**Core:**
- **WEBHOOK_SECRET**: Required for webhook verification
- **TARGET_REPO_URL**: Required - repository to target for Builder
- **GITHUB_TOKEN**: Optional but important for private repos and API operations
- **BOOTY_OWN_REPO_URL**: For self-modification detection
- **BOOTY_SELF_MODIFY_ENABLED**: Must be explicitly true for self-modification

**GitHub App (Verifier & Security):**
- **GITHUB_APP_ID**: GitHub App ID for check runs
- **GITHUB_APP_PRIVATE_KEY**: Private key for GitHub App authentication
- **GITHUB_APP_INSTALLATION_ID**: Installation ID for the app

**LLM Settings:**
- Configured via magentic environment variables
- **MAGENTIC_BACKEND**: LLM backend (e.g., anthropic)
- **MAGENTIC_ANTHROPIC_API_KEY**: Anthropic API key

**Memory System:**
- **MEMORY_ENABLED**: Enable memory ingestion and surfacing
- **MEMORY_RETENTION_DAYS**: Keep records within this window (default: 90)
- **MEMORY_MAX_MATCHES**: Max matches per PR comment (default: 3)
- **MEMORY_STATE_DIR**: State directory for memory.jsonl

**Security Agent:**
- **SECURITY_ENABLED**: Master switch for security checks
- **SECURITY_FAIL_SEVERITY**: Severity threshold (low, medium, high, critical)

**Release Governor:**
- **RELEASE_GOVERNOR_ENABLED**: Enable deployment gating
- **RELEASE_GOVERNOR_APPROVED**: Override for manual approval

**Observability:**
- **SENTRY_DSN**: Sentry DSN for error tracking
- **SENTRY_WEBHOOK_SECRET**: Webhook secret for Sentry integration

### .booty.yml Configuration
Repository-level configuration in `.booty.yml` (schema_version: 1):

```yaml
schema_version: 1
setup_command: python3 -m venv .venv
install_command: .venv/bin/pip install -e '.[dev]'
test_command: .venv/bin/pytest
max_files_changed: 30      # Verifier limit
max_diff_loc: 1500         # Verifier limit

security:
  enabled: true
  fail_severity: high
  secret_scanner: gitleaks
  sensitive_paths:
    - ".github/workflows/**"
    - "infra/**"

release_governor:
  enabled: true
  verification_workflow_name: "Verify main"
  deploy_workflow_name: deploy.yml

memory:
  enabled: true
  retention_days: 90
  max_matches: 3
  comment_on_pr: true
  comment_on_incident_issue: true
```

### Path Restrictions
Protected paths (configured in RESTRICTED_PATHS):
- `.github/workflows/**` - CI/CD configurations
- `.env`, `.env.*`, `**/*.env` - Environment files
- `**/secrets.*` - Secret files
- `Dockerfile`, `docker-compose*.yml` - Container configs
- `*lock.json`, `*.lock` - Dependency lockfiles

## Build and Run

### Installation
```bash
pip install -e .           # Install in development mode
pip install -e ".[dev]"    # Install with dev dependencies
```

### Running
```bash
# Set environment variables in .env file (see .env.example)
uvicorn booty.main:app --reload  # Development mode
booty                             # Production mode (if installed)
```

### Testing
```bash
pytest                    # Run all tests
pytest tests/test_*.py    # Run specific test file
pytest -v                 # Verbose output
pytest -k "test_name"     # Run specific test by name
```

### CLI Commands
```bash
# System status
booty status              # Show agent status (Builder, Verifier, Governor, Memory)

# Verifier
booty verifier check-test --repo owner/repo --sha <sha> --installation-id <id>
booty verifier status

# Release Governor
booty governor status                      # Show release state
booty governor simulate <sha>              # Dry-run decision
booty governor simulate --sha <sha> --show-paths
booty governor trigger <sha>               # Manual deploy trigger

# Memory
booty memory status                        # Show memory state
booty memory query --pr <num> --repo owner/repo
booty memory query --sha <sha> --repo owner/repo

# Output options: add --json for machine-readable output
```

## Key Patterns and Conventions

### Magentic LLM Functions
- Use `@prompt` decorator for LLM function calls
- Define return types as Pydantic models for structured output
- Keep prompts focused and specific
- Include examples in prompts when helpful
- Use `@prompt_chain` for multi-step reasoning

### Job Processing
- Jobs are queued and processed asynchronously by worker pool
- Each job gets a fresh workspace (clean clone)
- Job state is tracked: QUEUED → RUNNING → COMPLETED/FAILED
- Duplicate deliveries are filtered by delivery_id

### Workspace Isolation
- Fresh clone created for each job in temp directory
- Workspace is cleaned up after job completes (success or failure)
- No shared state between jobs
- Branch created per issue: `booty/issue-{issue_number}`

### Self-Modification Safety
- Target repo URL compared against BOOTY_OWN_REPO_URL
- Must explicitly enable with BOOTY_SELF_MODIFY_ENABLED=true
- Additional validation gates for self-targeting PRs
- Restricted paths enforced more strictly for self-modification

### Token Budget Management
- Context window managed by TokenBudget class
- Uses Anthropic token counting API for accuracy
- Files prioritized and truncated to fit budget
- Conservative buffer maintained (180K tokens default)

### Structured Logging
- Use bound loggers with context: `logger.bind(job_id=...)`
- Use snake_case for log message keys
- Include relevant context in every log message
- Use appropriate levels: info, warning, error

### Git Operations
- Always use --no-pager for git commands in scripts
- Create feature branches from target branch
- Commit messages format: verb + description
- Push to remote immediately after commit

### GitHub Check Runs (Verifier & Security)
- Use GitHub Checks API for status reporting
- Create check run at start (queued → in_progress)
- Update with conclusion (success, failure, neutral) and output
- Add annotations for specific file/line issues
- Verifier uses `booty/verifier` check name
- Security uses `booty/security` check name

### Memory Integration
- Use `memory.api.add_record()` to store events
- Include type, repo, sha, fingerprint for deduplication
- Records are JSONL append-only (no updates)
- Query with `memory.lookup` for PR/SHA matches
- Surface matches using `memory.surfacing.format_comment()`

### Release Governor Decision Flow
1. Load release state from state_dir
2. Get production_sha (current or previous)
3. Compute risk from diff pathspecs
4. Apply decision rules (hard holds, cooldown, rate limit, approval)
5. ALLOW → trigger workflow_dispatch with SHA
6. HOLD → post commit status with reason and unblock instructions

### Security Agent Pattern
- Three-stage pipeline: secret scan → dependency audit → permission drift
- PASS: All clean, post success check
- FAIL: Secrets or vulnerabilities found, post failure check with annotations
- ESCALATE: Sensitive paths touched, post success check but persist override for Governor

### Verifier Agent Pattern
- Load .booty.yml from PR head via GitHub API
- Validate schema, limits (files/LOC), imports/compile
- Post check run with validation results
- On failure: surface error + trigger Memory record + optionally re-enqueue Builder

## Constraints

- **No polling**: System is webhook-driven only
- **Fresh clones**: No persistent repository state
- **No custom UI**: Interface is GitHub (issues in, PRs out)
- **File generation**: Full file content, not diffs (LLMs struggle with patches)
- **Self-modification**: Requires explicit opt-in and has safety gates
- **Path restrictions**: Some paths are always protected (workflows, secrets)

## Anti-Patterns to Avoid

- Don't use sync file I/O in async contexts
- Don't hardcode repository URLs or tokens
- Don't catch and ignore exceptions silently
- Don't create stateful globals (except job_queue)
- Don't use shell=True in subprocess calls
- Don't commit secrets or credentials
- Don't modify protected paths
- Don't use abbreviations in variable names
- Don't write functions longer than 100 lines

## Common Tasks

### Adding a New LLM Prompt
1. Define return type as Pydantic model in `llm/models.py`
2. Create prompt function in `llm/prompts.py` with `@prompt` decorator
3. Use the function in appropriate module (generator, refiner, etc.)

### Adding New Configuration
1. Add field to Settings class in `config.py`
2. Add default value or mark as required
3. Document in `.env.example`
4. Access via `get_settings()` function

### Adding New API Endpoint
1. Create router function in appropriate module
2. Add route to FastAPI app in `main.py`
3. Use structured logging for request tracking
4. Return appropriate HTTP status codes

### Modifying Code Generation
1. Primary logic is in `code_gen/generator.py`
2. Refinement loop is in `code_gen/refiner.py`
3. Add new LLM prompts in `llm/prompts.py`
4. Update token budget if adding file reading

### Adding Safety Checks
1. Path restrictions go in RESTRICTED_PATHS config
2. Self-modification gates in `self_modification/safety.py`
3. Validation logic in `code_gen/validator.py`
4. Security checks in `code_gen/security.py`

### Working with Verifier
1. Job definition in `verifier/job.py`
2. Main pipeline in `verifier/runner.py`
3. Add limit checks in `verifier/limits.py`
4. Import detection in `verifier/imports.py`
5. Post check runs via `github/checks.py`

### Working with Security Agent
1. Job definition in `security/job.py`
2. Main pipeline in `security/runner.py`
3. Secret scanning in `security/scanner.py` (gitleaks/trufflehog)
4. Dependency audit in `security/audit.py`
5. Permission drift in `security/permission_drift.py`
6. Persist overrides for Governor in state_dir

### Working with Release Governor
1. Handler in `release_governor/handler.py`
2. Decision logic in `release_governor/decision.py`
3. Risk computation in `release_governor/risk.py`
4. Deploy trigger in `release_governor/deploy.py`
5. State persistence in `release_governor/store.py`
6. CLI commands: `booty governor status|simulate|trigger`

### Working with Memory
1. Add records via `memory/api.py` `add_record()`
2. Storage in `memory/store.py` (JSONL append-only)
3. Query via `memory/lookup.py`
4. Surfacing via `memory/surfacing.py`
5. Configure retention and matching in `.booty.yml`
6. CLI commands: `booty memory status|query`

### Adding Test Generation Support
1. Language detection in `test_generation/detector.py`
2. Framework detection from config files and patterns
3. Convention model in `test_generation/models.py`
4. Import validation in `test_generation/validator.py`
5. Called by Builder during code generation
