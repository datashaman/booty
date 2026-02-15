# Booty - GitHub Copilot Instructions

## Project Overview

Booty is a self-managing software builder powered by AI. It receives GitHub issues via webhook, analyzes them with an LLM, generates code changes, runs tests with iterative refinement, and opens pull requests — including against its own repository with additional safety gates.

**Core Value**: A Builder agent that can take a GitHub issue and produce a working PR with tested code.

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
├── config.py            # Pydantic Settings for environment config
├── jobs.py              # Job queue and worker management
├── logging.py           # Structured logging configuration
├── repositories.py      # Workspace preparation and Git cloning
├── webhooks.py          # GitHub webhook signature verification
├── code_gen/            # Code generation and refinement
│   ├── generator.py     # Main issue-to-PR pipeline orchestrator
│   ├── refiner.py       # Test-driven code refinement loop
│   ├── security.py      # Path restrictions and safety checks
│   └── validator.py     # Generated code validation
├── llm/                 # LLM interaction layer
│   ├── prompts.py       # Magentic prompt functions
│   ├── models.py        # Pydantic models for LLM responses
│   └── token_budget.py  # Token counting and context management
├── git/                 # Git operations
│   └── operations.py    # Commit, push, branch operations
├── github/              # GitHub API operations
│   ├── comments.py      # Issue/PR comment posting
│   └── pulls.py         # PR creation and management
├── self_modification/   # Self-modification safety
│   ├── detector.py      # Detect if target is self
│   └── safety.py        # Self-modification gates
└── test_runner/         # Test execution
    └── runner.py        # Pytest test runner with output capture
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
- **Required**: WEBHOOK_SECRET, TARGET_REPO_URL
- **Optional but important**: GITHUB_TOKEN (for private repos)
- **LLM Settings**: Configured via magentic environment variables (MAGENTIC_BACKEND, MAGENTIC_ANTHROPIC_API_KEY, etc.)
- **Self-modification**: BOOTY_SELF_MODIFY_ENABLED must be explicitly true

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
