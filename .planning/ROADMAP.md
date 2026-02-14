# Roadmap: Booty

## Overview

Booty evolves from webhook handler to self-managing builder in four phases. Phase 1 establishes reliable webhook-to-workspace infrastructure with async job processing. Phase 2 adds LLM-powered issue analysis and code generation to deliver end-to-end issue-to-PR automation. Phase 3 introduces test execution with iterative refinement loops to ensure quality. Phase 4 activates the unique differentiator: Booty building Booty through self-modification.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Webhook-to-Workspace Pipeline** - Foundation infrastructure without LLM complexity
- [x] **Phase 2: LLM Code Generation** - Core value delivery with issue-to-PR automation
- [ ] **Phase 3: Test-Driven Refinement** - Quality assurance through testing and iteration
- [ ] **Phase 4: Self-Modification** - Booty builds Booty

## Phase Details

### Phase 1: Webhook-to-Workspace Pipeline

**Goal**: Receive GitHub webhook events and prepare isolated workspaces for code generation

**Depends on**: Nothing (first phase)

**Requirements**: REQ-01, REQ-02, REQ-03, REQ-04, REQ-05, REQ-06, REQ-17

**Components built**:
- Configuration Store (environment-based config with Pydantic validation)
- Webhook Gateway (FastAPI endpoint with HMAC signature verification)
- Repository Manager (fresh clone to temp directories, branch creation, cleanup)
- Event Orchestrator (basic job state tracking, async execution)
- Structured logging foundation (correlation IDs, JSON output)

**Success Criteria** (what must be TRUE):
  1. Webhook handler receives GitHub issue labeled events and returns 200 OK within 2 seconds
  2. Job processing happens asynchronously after webhook returns (no blocking)
  3. Each job gets a fresh clone of the target repository in an isolated temporary directory
  4. Same webhook event delivered twice produces no duplicate jobs (idempotency)
  5. All operations produce JSON logs with correlation IDs linking event to job to actions
  6. Target repository URL, branch, and label are configurable via environment variables

**Key Risks** (from pitfalls research):
- Webhook timeout death spiral: Synchronous processing causes GitHub retries creating duplicate jobs
  - Mitigation: Enqueue immediately, process async, return 200 OK fast
- Stateful memory corruption: Reused state leaks between tasks
  - Mitigation: Fresh clone per task, cleanup after completion
- Non-deterministic configuration: Hardcoded values prevent reproducibility
  - Mitigation: All params configurable, temperature=0 default, sorted file lists

**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Project skeleton, configuration store, and structured logging
- [x] 01-02-PLAN.md — Webhook handler, async job queue, and repository manager

### Phase 2: LLM Code Generation

**Goal**: Analyze GitHub issues and generate working code changes as pull requests

**Depends on**: Phase 1 (needs workspace isolation and job orchestration)

**Requirements**: REQ-07, REQ-08, REQ-09, REQ-10, REQ-11, REQ-15

**Components built**:
- Issue Analyzer (magentic-based LLM extraction of requirements from issue text)
- Code Generator (LLM code production with context budgeting, applies changes to workspace)
- Git Operator (conventional commits, branch push, PR creation via PyGithub)
- Context budget tracking (token counting, file selection, overflow detection)
- Basic security controls (path restrictions, input sanitization)

**Success Criteria** (what must be TRUE):
  1. System analyzes issue content and produces structured understanding of what needs to change
  2. Generated code changes are syntactically valid and apply cleanly to the workspace
  3. System can modify, create, or delete multiple files in a coordinated way (function + import + test)
  4. Pull request appears on GitHub with conventional commit message, structured description, and issue reference
  5. LLM calls never exceed token limits (budget tracking prevents context overflow)
  6. Generated code changes are restricted to allowed paths (no modifications to .github/workflows, .env)

**Key Risks** (from pitfalls research):
- Context window blindness: Agent exceeds token limits, hallucinates code
  - Mitigation: Token budgets, overflow detection, smart file selection
- Prompt injection: Malicious issue content extracts secrets or bypasses security
  - Mitigation: Treat issue content as untrusted, path restrictions, output validation
- Non-determinism: Same issue produces different code each run
  - Mitigation: temperature=0, seeding, deterministic file ordering

**Plans**: 5 plans

Plans:
- [x] 02-01-PLAN.md — Dependencies, config settings, and Pydantic LLM models
- [x] 02-02-PLAN.md — Path security restrictions and code validation
- [x] 02-03-PLAN.md — Git commit/push operations and PR creation
- [x] 02-04-PLAN.md — LLM prompts (issue analysis, code generation) and token budget
- [x] 02-05-PLAN.md — Orchestrator wiring into process_job pipeline

### Phase 3: Test-Driven Refinement

**Goal**: Ensure generated code passes tests through iterative refinement with failure feedback

**Depends on**: Phase 2 (needs working code generation)

**Requirements**: REQ-12, REQ-13, REQ-14

**Components built/modified**:
- Test Runner (subprocess execution with timeout, captures pass/fail status and output)
- Event Orchestrator enhancement (retry loops with feedback, max attempt limits)
- Error notification system (GitHub issue comments, draft PR with partial work)
- Retry strategy (exponential backoff for transient errors, iteration limits)

**Success Criteria** (what must be TRUE):
  1. System runs target repository's test suite and captures exit code, stdout, stderr
  2. On test failure, system feeds error output back to LLM and regenerates code (iterative refinement)
  3. System retries up to N times (configurable) before giving up, each iteration includes previous error context
  4. When tests pass, PR is created as ready for review (not draft)
  5. On permanent failure after max retries, system comments on issue with error details and opens draft PR if any work exists
  6. Transient errors (API timeout, rate limit) retry with exponential backoff instead of failing immediately

**Key Risks** (from pitfalls research):
- Tests passing does not equal quality: Green tests can mask security issues or convention violations
  - Mitigation: Consider adding linters/formatters to validation pipeline (v2 scope)
- Infinite retry loops: System wastes resources on unfixable issues
  - Mitigation: Configurable max retries, exponential backoff, clear failure signals

**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Test runner module: .booty.yml config, async subprocess executor, output parser
- [x] 03-02-PLAN.md — GitHub failure handling: draft PR support, issue failure comments
- [x] 03-03-PLAN.md — Refinement loop, LLM regeneration prompt, pipeline integration

### Phase 4: Self-Modification

**Goal**: Enable Booty to process issues against its own repository with the same quality gates as external repos

**Depends on**: Phase 3 (needs proven reliable pipeline with quality gates)

**Requirements**: REQ-16

**Components built/modified**:
- Self-referential configuration (Booty repo as valid target)
- Enhanced safety rails for self-modification (additional path restrictions, human approval hooks)
- Bootstrap validation (verify initial Booty code handles self-building)

**Success Criteria** (what must be TRUE):
  1. When target repository is configured to Booty's own repo, the same pipeline executes (analyze, generate, test, PR)
  2. Self-generated PRs follow the same quality gates as external repo PRs (tests must pass, iterative refinement applies)
  3. Self-modification PRs are marked for human review (no auto-merge)
  4. Changes to Booty's core workflow files (.github/workflows, configuration) are flagged or require additional approval
  5. Booty can successfully process a real GitHub issue against itself and produce a working PR that improves Booty

**Key Risks** (from pitfalls research):
- Self-modification breaks Booty: Agent corrupts itself and becomes non-functional
  - Mitigation: Extra quality gates for self-PRs, human approval required, gradual rollout
- Bootstrap paradox: Initial code can't handle self-building complexity
  - Mitigation: Validate bootstrap sequence during planning, start with simple self-issues

**Plans**: TBD

Plans:
- [ ] TBD during planning

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Webhook-to-Workspace Pipeline | 2/2 | Complete | 2026-02-14 |
| 2. LLM Code Generation | 5/5 | Complete | 2026-02-14 |
| 3. Test-Driven Refinement | 0/3 | Not started | - |
| 4. Self-Modification | 0/TBD | Not started | - |
