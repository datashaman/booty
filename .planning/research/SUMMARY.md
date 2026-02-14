# Project Research Summary

**Project:** Booty - AI-Powered Builder Agent
**Domain:** Webhook-triggered GitHub automation with LLM code generation
**Researched:** 2026-02-14
**Confidence:** MEDIUM-HIGH

## Executive Summary

Booty is a webhook-triggered GitHub automation system that converts labeled issues into pull requests via LLM-powered code generation. Expert implementations of this domain follow an **async event-driven pipeline** architecture: webhooks enqueue jobs immediately (avoiding timeout death spirals), then heavy processing happens asynchronously with fresh workspace isolation per task. The core workflow is deterministic: clone → analyze → generate → test → commit → PR, with retry-with-feedback loops for test failures.

The recommended stack centers on **magentic** (constraint) for LLM abstraction, **FastAPI** for webhook handling, **PyGithub** for GitHub API, and **GitPython** for repository operations. This combination provides type safety, async support, and clean separation between prompt logic and business logic. The key architectural insight is that components must be stateless with clear boundaries - Repository Manager handles cloning, Issue Analyzer extracts requirements, Code Generator produces changes, Test Runner validates, and Git Operator publishes. Temperature=0 determinism and context budgeting are foundational, not optional.

Critical risks include context window overflow (causing hallucinated code), webhook timeout death spirals (creating duplicate PRs), and prompt injection via malicious issue content. Mitigation requires: token budget tracking with smart file selection, immediate job enqueuing with async processing, and treating issue content as untrusted input with path restrictions. Build these guardrails in Phase 1 - retrofitting them requires rewrites.

## Key Findings

### Recommended Stack

The stack research identified mature, well-integrated Python libraries optimized for async webhook handling and type-safe LLM interactions. No experimental dependencies - everything is production-grade with active maintenance.

**Core technologies:**
- **magentic 0.28+**: LLM abstraction layer (constraint) - decorator-based, supports OpenAI/Anthropic/LiteLLM, clean API for prompt management
- **FastAPI 0.109+**: Webhook server - async support, built-in Pydantic validation, minimal boilerplate for signature verification
- **PyGithub 2.1+**: GitHub API client - most mature option, comprehensive v3 API coverage, strong typing
- **GitPython 3.1+**: Git operations - Pythonic API, better error handling than subprocess, handles cloning and branching
- **httpx 0.26+**: HTTP client - async support matching FastAPI, modern API, used under the hood by GitHub libraries
- **structlog 24.1+**: Logging - structured output for agent observability, critical for debugging LLM decisions

**What to avoid:**
- Flask (synchronous, no built-in validation)
- Langchain (over-abstraction, magentic is sufficient)
- Celery/RQ for v1 (overkill, simple async sufficient)
- Polling libraries (webhooks are constraint)

**Key unknowns requiring validation:**
- Which LLM backend for code quality (GPT-4 vs Claude)
- Token limit handling for large repos (may need summarization)
- Test execution timeouts (configurable per repo)
- GitHub App vs PAT auth approach

### Expected Features

Feature research reveals a clear distinction between table stakes (users expect), differentiators (competitive advantage), and anti-features (avoid building).

**Must have (table stakes):**
- Issue → PR automation - core value proposition, end-to-end flow
- Code that compiles/runs - basic quality bar, broken code worse than no code
- Test execution - users need confidence changes work
- PR with explanation - context for reviewers
- Clean workspace isolation - fresh state per task prevents contamination
- Webhook-based triggering - event-driven, standard integration
- Label-based filtering - explicit opt-in per issue
- Multi-file changes - real features span files
- Idempotency - don't reprocess handled issues

**Should have (competitive differentiators):**
- **Self-modification capability** - agent improves itself, unique to Booty
- **Iterative refinement** - retry code generation on test failures until passing
- **Error recovery basics** - graceful failures build trust

**Defer to v2+:**
- Multi-agent architecture (very high complexity)
- Deep codebase understanding (semantic analysis)
- Learning from feedback (preference learning)
- Architecture-aware changes (pattern detection)

**Explicitly avoid (anti-features):**
- Auto-merge without approval - dangerous, erodes trust
- Custom UI/dashboard early - GitHub is the UI, premature
- Fine-tuned models - expensive, off-the-shelf sufficient
- Deployment automation - separate concern from PR creation
- Real-time chat interface - issue-based workflow clearer

### Architecture Approach

The architecture follows async event-driven pipeline patterns from mature GitHub bots (Dependabot, Renovate) and LLM agent systems. Key principle: stateless components with clear interfaces, fresh isolation per task.

**Major components:**
1. **Webhook Gateway** - validates signatures, routes events, returns 200 OK immediately (does NOT process)
2. **Event Orchestrator** - job lifecycle (queued/running/completed/failed), retry logic, status tracking
3. **Repository Manager** - fresh clones to temp directories, credential management, branch creation, cleanup
4. **Issue Analyzer** - LLM extraction of requirements from issue text, identifies relevant files
5. **Code Generator** - LLM code production with context budgeting, applies changes to workspace
6. **Test Runner** - executes tests via subprocess, captures results, feeds errors back to generator
7. **Git Operator** - commits with conventional messages, pushes branch, creates PR via API
8. **Configuration Store** - manages credentials, LLM settings, timeouts via .env + Pydantic

**Critical patterns:**
- Async job processing: webhook returns immediately, work happens asynchronously
- Workspace isolation: `tempfile.mkdtemp()` per job, `shutil.rmtree()` cleanup
- Retry with feedback: test failures loop back to code generation with error context
- Context budgeting: never exceed token limits, prune files to fit window

**Build order (dependency-driven):**
1. Tier 1 (foundation): Configuration Store, Webhook Gateway
2. Tier 2 (core ops): Repository Manager, Test Runner
3. Tier 3 (LLM): Issue Analyzer, Code Generator
4. Tier 4 (output): Git Operator
5. Tier 5 (orchestration): Event Orchestrator

### Critical Pitfalls

**1. Context Window Blindness**
Agent exceeds LLM token limits, silently truncates critical information, generates hallucinated code. Prevention: implement token budgets, AST-based context pruning, overflow detection. Must address in Phase 1.

**2. Test Passing ≠ Code Quality**
Green tests mask security vulnerabilities, convention violations, technical debt. Prevention: run linters/security scanners BEFORE tests, add quality gates. Phase 2-3 enhancement.

**3. Webhook Timeout Death Spiral**
Synchronous processing times out, GitHub retries create duplicate jobs, chaos. Prevention: enqueue job and return 200 OK immediately, idempotency keys. Foundational to Phase 1 architecture.

**4. Stateful Memory Corruption**
Reused state leaks between tasks, code from Repo A appears in Repo B. Prevention: fresh clone per task (Booty already has this - keep it), new LLM session per job. Phase 1.

**5. Prompt Injection via Issue Content**
Malicious issue extracts secrets or bypasses security. Prevention: treat issue content as untrusted, structured prompts, path restrictions, output validation. Basic protections Phase 1, enhanced Phase 2-3.

**6. LLM Non-Determinism Breaks Reproducibility**
Same issue produces different code each run, can't debug or test. Prevention: set temperature=0, seed parameter, sort file lists deterministically. Phase 1 configuration.

## Cross-Cutting Themes

Patterns that emerged across multiple research dimensions:

**1. Async-first architecture is non-negotiable**
- STACK: FastAPI for async webhooks, httpx for async HTTP
- ARCHITECTURE: Webhook Gateway enqueues immediately, async job processing
- PITFALLS: Synchronous processing causes timeout death spirals (critical pitfall)

**2. Context management is foundational, not a nice-to-have**
- STACK: Token budgets for magentic calls
- ARCHITECTURE: Context budgeting pattern, smart file selection
- PITFALLS: Context overflow causes hallucinations (critical pitfall)

**3. Isolation prevents entire classes of bugs**
- STACK: Fresh clones via GitPython + tempfile
- ARCHITECTURE: Workspace isolation pattern, cleanup after jobs
- PITFALLS: Stateful memory corruption (critical pitfall)
- FEATURES: Clean workspace isolation (table stakes)

**4. Quality gates must exist before scaling**
- FEATURES: Test execution is table stakes, code style consistency expected
- PITFALLS: Passing tests ≠ quality without linters/security scans
- ARCHITECTURE: Test Runner component, validation before PR

**5. Self-modification is differentiating but requires careful design**
- FEATURES: Unique differentiator for Booty
- PITFALLS: Needs guardrails to prevent corruption
- ARCHITECTURE: Must respect same isolation/quality patterns as regular repos

## Critical Decisions Needed Before Implementation

### 1. LLM Backend Selection
**Decision:** OpenAI GPT-4 vs Anthropic Claude for code generation
**Why critical:** Affects code quality, cost, latency
**Validation needed:** Generate test code with both, compare quality/cost/speed
**Recommendation:** Start with Claude (stronger code generation reputation per training data), make configurable

### 2. Authentication Strategy
**Decision:** GitHub App (scoped tokens, auto-expiring) vs Personal Access Token (simpler but less secure)
**Why critical:** Security posture, permission model
**Recommendation:** GitHub App for production (better security), support PAT for development ease

### 3. Task Queue vs Simple Async
**Decision:** Use task queue (Celery/RQ) in v1 or defer to v2
**Why critical:** Affects architecture complexity, scalability path
**Recommendation:** Simple asyncio tasks for v1 (matches architecture tier 5 build order), add queue when concurrent job processing needed

### 4. Sandboxing Approach
**Decision:** Subprocess with timeout vs Docker containers
**Why critical:** Security vs complexity tradeoff
**Recommendation:** Subprocess for v1 (simple, fast), Docker for production (stronger isolation)

### 5. Determinism Configuration
**Decision:** Temperature setting for LLM calls
**Why critical:** Reproducibility for debugging, testing
**Recommendation:** temperature=0 from day one (non-negotiable per PITFALLS)

### 6. Context Pruning Strategy
**Decision:** How to select files when codebase exceeds context window
**Why critical:** Quality of generated code depends on relevant context
**Recommendation:** Phase 1 simple (imports + modified files only), Phase 2 AST-based relevance ranking

## MVP Scope Recommendation

Synthesizing across all four research dimensions:

### Phase 1: Webhook-to-Workspace Pipeline (Foundation)
**Core goal:** Receive webhook, clone repo, respond to events
**Why first:** No dependencies, validates architecture, avoids webhook timeout pitfall
**Components:** Configuration Store, Webhook Gateway, Repository Manager, Test Runner (basic)
**Features:** Webhook triggering, label filtering, fresh workspace isolation, idempotency
**Stack:** FastAPI + PyGithub + GitPython + python-dotenv + Pydantic
**Quality gates:** Webhook signature verification, job state tracking, structured logging
**Avoids pitfalls:** #3 (webhook timeout), #4 (workspace isolation), #6 (deterministic config)
**Complexity:** Low-Medium (all table stakes features)
**Research needed:** None (standard patterns)

### Phase 2: LLM Code Generation (Core Value)
**Core goal:** Analyze issues, generate code, create PRs
**Why second:** Builds on Phase 1 workspace, delivers end-to-end value
**Components:** Issue Analyzer, Code Generator, Git Operator
**Features:** Issue → PR automation, code generation that compiles, PR with explanation
**Stack:** Add magentic, structlog for LLM observability
**Quality gates:** Context budget tracking, temperature=0, conventional commits
**Avoids pitfalls:** #1 (context management), #5 (basic input sanitization), #6 (determinism)
**Complexity:** Medium (LLM integration, prompt engineering)
**Research needed:** Prompt templates for analysis/generation, context pruning strategy

### Phase 3: Test-Driven Refinement (Quality)
**Core goal:** Run tests, iterate on failures, ensure quality
**Why third:** Requires working code generation, adds reliability
**Components:** Event Orchestrator (ties pipeline together), Test Runner (enhanced)
**Features:** Test execution, iterative refinement, error recovery
**Stack:** No new dependencies (use subprocess + pytest)
**Quality gates:** Retry loops with feedback, failure notifications
**Avoids pitfalls:** #2 (add linters to validation), #10 (failure recovery)
**Complexity:** Medium-High (feedback loops, retry logic)
**Research needed:** Retry strategies, test output parsing

### Phase 4: Self-Modification (Differentiator)
**Core goal:** Booty can build Booty
**Why fourth:** Needs all prior phases working, highest risk
**Components:** All components (self-referential)
**Features:** Self-modification capability with safety rails
**Stack:** No new dependencies (same pipeline, different target repo)
**Quality gates:** Enhanced path restrictions, human approval gates for self-PRs
**Avoids pitfalls:** All prior mitigations apply, extra scrutiny on self-changes
**Complexity:** High (bootstrap logic, safety considerations)
**Research needed:** Self-modification patterns, safety rails, bootstrap sequences

### Phase 5+: Enhancements (Post-MVP)
**Defer until core value proven:**
- Multi-agent architecture (very high complexity)
- Deep codebase understanding (semantic analysis)
- Security scanning integration
- Performance profiling
- Documentation generation
- Learning from feedback

## Implications for Roadmap

### Phase Ordering Rationale

**Foundation → Value → Quality → Differentiation** progression:

1. **Phase 1 establishes infrastructure without LLM complexity.** This allows validating webhook handling, workspace management, and GitHub API integration independently. Addresses critical pitfall #3 (webhook timeouts) immediately.

2. **Phase 2 delivers end-to-end value but without quality guarantees.** Users can see PRs generated, provides feedback loop for prompt engineering. Addresses critical pitfalls #1 (context) and #6 (determinism).

3. **Phase 3 adds reliability through testing.** Builds trust in system output, enables iterative improvement. Addresses pitfall #2 (quality gates).

4. **Phase 4 activates unique differentiator.** Self-modification only makes sense when core pipeline is proven reliable. High risk justified by proven foundation.

**Why this order avoids common failures:**
- Delays LLM integration until infrastructure solid (prevents debugging infrastructure issues masked by LLM non-determinism)
- Separates concerns for testing (webhook routing testable independently from code generation)
- Allows incremental prompt engineering (Phase 2) before feedback loops (Phase 3)
- Defers highest-risk feature (self-modification) until maximum confidence

**Component build order alignment:**
- Phase 1: Tiers 1-2 (Config, Webhook Gateway, Repo Manager, basic Test Runner)
- Phase 2: Tier 3 + Tier 4 (Issue Analyzer, Code Generator, Git Operator)
- Phase 3: Tier 5 (Event Orchestrator completes the pipeline)
- Phase 4: No new components (applies existing pipeline to self)

### Research Flags

**Needs deeper research during planning:**

- **Phase 2 (LLM Code Generation):**
  - Prompt template design for issue analysis and code generation
  - Context pruning strategies for different repo sizes
  - LLM backend comparison (GPT-4 vs Claude code quality)
  - Token budget allocation across analysis and generation

- **Phase 3 (Test-Driven Refinement):**
  - Retry strategies (how many attempts, backoff timing)
  - Test output parsing for different frameworks (pytest, unittest, etc.)
  - Feedback formatting for LLM (how to present errors effectively)

- **Phase 4 (Self-Modification):**
  - Bootstrap sequence (how Booty builds first version of itself)
  - Safety rails specific to self-modification
  - Human approval workflow for self-PRs

**Standard patterns (skip research-phase):**

- **Phase 1:** Webhook handling, git operations, workspace management all have well-documented patterns
- **Phase 5+:** Can research when actually planning these phases post-MVP

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Mature libraries, established patterns, no exotic dependencies. Magentic is newer but documented. |
| Features | MEDIUM | Table stakes clear from domain analysis. Differentiators based on product vision. Unknown: actual user priorities. |
| Architecture | HIGH | Event-driven webhook patterns proven by Dependabot/Renovate. LLM agent patterns established. |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls well-documented in LLM/webhook domains. Unknown: Booty-specific edge cases. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

**During Phase 1 planning:**
- Exact GitHub webhook signature verification implementation (FastAPI + hmac pattern)
- Job state persistence strategy (in-memory for v1, database for v2?)
- Error notification mechanism (GitHub issue comments? Status API?)

**During Phase 2 planning:**
- Prompt templates require iteration - start simple, refine based on output quality
- Context budget allocation needs testing with real repos (small/medium/large)
- LLM backend selection requires practical comparison

**During Phase 3 planning:**
- Test framework detection strategy (pytest vs unittest vs others)
- Retry limit tuning based on actual failure patterns
- Linter/formatter integration (detect from repo config)

**During Phase 4 planning:**
- Self-modification safety rails need careful design review
- Bootstrap sequence needs validation (can initial Booty code handle self-building?)

**Post-MVP unknowns:**
- GitHub App setup process (if chosen over PAT)
- Rate limit handling for high-volume repos
- Large repo optimization (sparse checkout, shallow clone)
- Multi-repo coordination patterns (for projects with dependencies)

## Risk Summary with Mitigations

| Risk | Impact | Likelihood | Mitigation | Phase |
|------|--------|-----------|------------|-------|
| Context overflow hallucinates code | HIGH | HIGH | Token budgets, context pruning, overflow detection | Phase 1 config, Phase 2 implementation |
| Webhook timeouts create duplicate PRs | HIGH | MEDIUM | Async job processing, idempotency keys | Phase 1 architecture |
| Tests pass but code is insecure/low-quality | MEDIUM | HIGH | Linters, security scans, quality gates | Phase 3 enhancement |
| Stateful corruption between jobs | HIGH | LOW | Fresh clone per task (already in design) | Phase 1 implementation |
| Prompt injection via malicious issues | MEDIUM | MEDIUM | Input sanitization, path restrictions, output validation | Phase 1 basic, Phase 2-3 enhanced |
| Non-deterministic output prevents debugging | MEDIUM | HIGH | temperature=0, seeding, deterministic file ordering | Phase 1 configuration |
| Self-modification breaks Booty | HIGH | MEDIUM | Extra quality gates, human approval, gradual rollout | Phase 4 design |
| LLM costs spiral out of control | MEDIUM | LOW | Token budgets, caching, monitoring | Phase 2 implementation |

## Sources

### Primary (HIGH confidence)
- Magentic documentation and GitHub repo (LLM abstraction patterns)
- FastAPI documentation (webhook handling, async patterns)
- PyGithub documentation (GitHub API v3 coverage)
- GitHub webhooks documentation (signature verification, event types)
- GitPython documentation (repository operations)

### Secondary (MEDIUM confidence)
- GitHub bot patterns from Dependabot/Renovate analysis (architecture patterns)
- LLM code generation best practices from training data (context management, quality gates)
- Event-driven architecture patterns (async job processing, queue patterns)
- Python ecosystem standards (pytest, structlog, pydantic)

### Tertiary (LOW confidence - needs validation)
- Magentic LLM backend performance comparison (needs testing)
- Token limit handling for large repos (needs profiling)
- Test execution timeout tuning (needs measurement)
- Self-modification safety patterns (needs research during Phase 4 planning)

---
*Research completed: 2026-02-14*
*Ready for roadmap: yes*
