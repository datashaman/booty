# Stack Research: Booty

## Recommended Stack

### Core
| Component | Library | Version | Confidence | Rationale |
|-----------|---------|---------|------------|-----------|
| LLM Abstraction | magentic | 0.28+ | HIGH | Constraint. Decorator-based, type-safe, supports OpenAI, Anthropic, LiteLLM. Active development, clean API. |
| GitHub API | PyGithub | 2.1+ | HIGH | Most mature and widely-used. Comprehensive coverage of GitHub API v3. Strong typing, active maintenance. |
| Webhook Server | FastAPI | 0.109+ | HIGH | Modern async, built-in validation with Pydantic, minimal boilerplate. Easy webhook signature verification. Better than Flask for webhooks due to async and typing. |
| Git Operations | GitPython | 3.1+ | MEDIUM | Pythonic API over git. Better error handling than subprocess. Risk: occasional git version compatibility issues. |
| HTTP Client | httpx | 0.26+ | HIGH | Async support (works with FastAPI), modern API. Used by many GitHub libraries under the hood. |
| Environment Config | python-dotenv | 1.0+ | HIGH | Standard for .env files. Simple, widely used. |
| Process Management | subprocess (stdlib) | — | HIGH | For running tests and isolated commands. No external deps. |

### Supporting
| Component | Library | Version | Confidence | Rationale |
|-----------|---------|---------|------------|-----------|
| Webhook Signature Verification | hmac (stdlib) | — | HIGH | GitHub uses HMAC-SHA256. Built-in, no deps needed. |
| JSON Validation | Pydantic | 2.5+ | HIGH | Included with FastAPI. Models for webhook payloads and config. Type-safe. |
| Logging | structlog | 24.1+ | MEDIUM | Structured logging for agent observability. Better than stdlib logging for agents. Alternative: loguru. |
| File Operations | pathlib (stdlib) | — | HIGH | Modern path handling. No external deps. |
| Testing | pytest | 8.0+ | HIGH | Standard for Python. Needed to run generated code tests. |
| Async Runtime | uvicorn | 0.27+ | HIGH | ASGI server for FastAPI. Production-ready, fast. |
| Sandboxing | docker-py | 7.0+ | MEDIUM | Run generated code in containers. Safer than bare subprocess. Requires Docker daemon. |
| Code Parsing | tree-sitter-python | 0.21+ | LOW | Optional: parse code to understand structure. Useful for complex agents. May be overkill for v1. |
| Diff Generation | difflib (stdlib) | — | HIGH | Generate human-readable diffs for PRs. Built-in. |

## What NOT to Use
| Library | Why Not |
|---------|---------|
| ghapi | Less mature than PyGithub despite being newer. Documentation sparse. Async might conflict with FastAPI patterns. |
| Flask | Synchronous, more boilerplate for webhooks, no built-in validation. FastAPI's Pydantic models better for webhook payloads. |
| Langchain | Over-abstraction for this use case. Magentic is a constraint and sufficient. Langchain adds complexity without clear benefit. |
| subprocess.call/os.system | Use subprocess.run instead. Better error handling, safer, modern. |
| GitPython alternatives (dulwich, pygit2) | Less Pythonic, more complex setup. dulwich is pure Python but slower. pygit2 requires libgit2 compilation. |
| Polling libraries (schedule, APScheduler) | Webhooks are a constraint. No polling needed. |
| Celery/RQ | Overkill for v1. Simple async webhook handler sufficient. Add task queue later if needed. |
| virtualenv/venv in-process | For sandboxing, use Docker containers instead. venv doesn't provide real isolation. |

## Key Considerations

### Magentic Deep Dive
- **Supported LLM Backends**: OpenAI (GPT-4, GPT-3.5), Anthropic (Claude), LiteLLM (80+ providers)
- **Key Features**: Function calling, streaming, prompt templating, retry logic, type coercion
- **Usage Pattern**: Decorate functions with `@prompt`, `@chatprompt`. Return types auto-parsed.
- **Strengths**: Clean separation of prompt logic from business logic. Type-safe.
- **Limitations**: Relatively new (2023+), smaller community than Langchain. Good for straightforward use cases.

### GitHub Webhook Security
- **Signature Verification**: CRITICAL. Use `hmac.compare_digest()` to verify `X-Hub-Signature-256` header.
- **Secret Storage**: Store webhook secret in environment variable, never commit.
- **Payload Validation**: Use Pydantic models for type-safe webhook payload parsing.
- **Event Filtering**: Check `X-GitHub-Event` header. Only process `issues` events with action `labeled`.

### Git Operations Strategy
- **Fresh Clone**: Use `GitPython.Repo.clone_from()` to clone into temp directories.
- **Workspace Management**: Use `tempfile.mkdtemp()` for per-task workspaces. Clean up with `shutil.rmtree()`.
- **Branch Strategy**: Create feature branch from target repo's default branch. Push to fork or target repo based on permissions.
- **Credentials**: Use GitHub App installation tokens (short-lived, auto-expiring) OR personal access tokens. Store in env.

### Sandboxing/Isolation Options
1. **Subprocess with Timeout** (GOOD for v1)
   - Use `subprocess.run(timeout=X)` to run tests
   - Runs on host but with time limits
   - Pros: Simple, fast, no external deps
   - Cons: Limited isolation, can still access file system

2. **Docker Containers** (RECOMMENDED for production)
   - Use `docker-py` to spin up containers per task
   - Mount cloned repo as volume
   - Run tests inside container
   - Pros: Strong isolation, reproducible environment
   - Cons: Requires Docker daemon, slower startup

## Unknowns / Needs Validation

### Critical Unknowns
1. **Magentic Backend Choice**: Which LLM provider/model for Builder? OpenAI GPT-4? Anthropic Claude? Test both for code generation quality.
2. **Token Limits**: How much context can Builder send to LLM? Large repos may exceed context windows. May need repo summarization strategy.
3. **Test Execution Timeout**: How long to wait for tests? Some test suites run 10+ minutes. Need configurable timeout.
4. **Rate Limits**: GitHub API rate limits (5000/hour authenticated). Does PyGithub handle this gracefully? Need retry logic.

### Technical Validation Needed
1. **GitPython + Large Repos**: Does GitPython handle large repos (1GB+) efficiently? May need sparse checkout or shallow clone.
2. **FastAPI + Long-Running Tasks**: Webhook response must be quick (<10s). Builder tasks take minutes. Need async task pattern (return 202 Accepted, process in background).
3. **GitHub App vs PAT**: Which auth method? GitHub Apps more secure (scoped, auto-expiring tokens) but more setup. PATs simpler but less secure.

### Design Validation Needed
1. **Error Handling**: What happens when Builder fails? Comment on issue? Close with label? Create error issue?
2. **PR Draft vs Ready**: Should Builder open draft PRs or ready-to-review? Draft safer for v1.
3. **Self-Management Bootstrap**: How does Booty handle PRs against itself? Manual merge for v1, then auto-merge with tests passing?

## Dependencies Summary

### Minimal v1 Stack
```txt
# Core
magentic>=0.28.0,<0.29.0
PyGithub>=2.1.1,<2.2.0
fastapi>=0.109.0,<0.110.0
uvicorn>=0.27.0,<0.28.0
httpx>=0.26.0,<0.27.0
GitPython>=3.1.40,<3.2.0

# Config & Validation
python-dotenv>=1.0.0,<2.0.0
pydantic>=2.5.0,<3.0.0

# Testing
pytest>=8.0.0,<9.0.0

# Logging (optional but recommended)
structlog>=24.1.0,<25.0.0
```

---

*Research completed: 2026-02-14*
*Confidence: MEDIUM-HIGH (no web search validation for latest versions, but libraries and patterns are established)*
