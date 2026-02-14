# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-14)

**Core value:** A Builder agent that can take a GitHub issue and produce a working PR with tested code — the foundation everything else builds on.
**Current focus:** Phase 3: Test-Driven Refinement

## Current Position

Phase: 3 of 4 (Test-Driven Refinement)
Plan: 3 of 3 in current phase
Status: Phase complete
Last activity: 2026-02-14 — Completed 03-03-PLAN.md

Progress: [███████░░░] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 10
- Average duration: 2.1 min
- Total execution time: 0.35 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 1 | 2/2 | 5 min | 3 min |
| Phase 2 | 5/5 | 11 min | 2 min |
| Phase 3 | 3/3 | 7 min | 2 min |

**Recent Trend:**
- Last 5 plans: 02-04 (3min), 02-05 (2min), 03-01 (2min), 03-02 (2min), 03-03 (3min)
- Trend: Consistent 2-3 min velocity maintained throughout Phase 3

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Start with Builder only: Avoid protocol/abstraction quicksand; let pain reveal what's needed
- Magentic for LLM abstraction: Decorator-based, type-safe, multi-backend; keeps agent code clean
- GitHub webhooks for triggering: Event-driven is cleaner than polling; integrates with existing workflow
- Fresh clone per task: Isolation prevents stale state leaking between tasks; simplicity over speed
- Label-based issue filtering: Not every issue should trigger a build; explicit opt-in via label
- Pydantic Settings for config (01-01): Type-safe environment variable validation
- LLM_TEMPERATURE defaults to 0.0 (01-01): Deterministic behavior per REQ-17
- Lazy singleton pattern (01-01): @lru_cache on get_settings() for test overrides
- HMAC verification before JSON parsing (01-02): Raw body must be read first for signature validation
- Delivery ID deduplication with 10k cap (01-02): Set-based tracking prevents unbounded memory growth
- Executor for git clone (01-02): GitPython is synchronous - must run in executor to avoid blocking
- Feature branch naming (01-02): agent/issue-{number} provides clear identification
- Pydantic BaseModel for LLM outputs (02-01): Type safety, validation, automatic retries with magentic
- Conservative context window budget (02-01): 180k tokens leaves room for output, handles estimation variance
- Full file generation model (02-01): FileChange.content is complete file, not diffs (LLMs struggle with diffs)
- pathspec for pattern matching (02-02): Gitignore-style patterns with ** support, not fnmatch or regex
- Canonical path resolution (02-02): pathlib.resolve() + is_relative_to() prevents traversal attacks
- Skip third-party import validation (02-02): Only validate stdlib and syntax; CI catches third-party import errors
- Async executor for git push (02-03): GitPython push operations must run in executor to avoid blocking event loop
- Plain dicts for PR file changes (02-03): Keep github module independent of llm.models for better modularity
- Token injection for authenticated push (02-03): Reuse Phase 1 pattern for HTTPS URL credential injection
- Anthropic token counting API (02-04): Official API provides accurate estimates for budget management
- UNTRUSTED content delimiters (02-04): Structural isolation prevents prompt injection, preserves full issue content
- Model as parameter pattern (02-04): Orchestrator configures model/temperature from settings, passes to prompts
- Sequential pipeline with fail-fast validation (02-05): Each step validates prerequisites before proceeding to prevent cascading failures
- Automatic file selection within token budget (02-05): On overflow, select files incrementally to degrade gracefully rather than fail
- Structured logging at every step (02-05): Full audit trail of pipeline execution for debugging and monitoring
- PyYAML for config parsing with Pydantic validation (03-01): yaml.safe_load() prevents arbitrary code execution, Pydantic provides type-safe validation
- asyncio.wait_for with proc.kill() + proc.wait() (03-01): Prevents zombie processes on timeout by properly reaping child processes
- Exclude test files from error extraction (03-01): Focus on source code that needs fixing, not test files themselves
- errors='replace' for UTF-8 decoding (03-01): Handle non-standard test output gracefully without blocking execution
- Last-failure-only context in refinement (03-03): Each iteration passes only latest test output to LLM, not cumulative history
- Tenacity retry for API errors (03-03): Exponential backoff for RateLimitError, APITimeoutError with 5 attempts max
- Draft PR on test failure (03-03): Failed tests create draft PR with error context, successful tests create ready PR

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-14 (plan execution)
Stopped at: Completed 03-03-PLAN.md
Resume file: None
