# Requirements: Booty

## v1 Scope

### REQ-01: Webhook Event Reception
**Category:** Table Stakes | **Complexity:** Medium | **Phase:** 1
The system receives GitHub webhook events, validates signatures using HMAC-SHA256, filters for issue `labeled` events matching the configured label (e.g. `agent:builder`), and enqueues jobs immediately (returning 200 OK within seconds).

### REQ-02: Idempotent Job Processing
**Category:** Table Stakes | **Complexity:** Low | **Phase:** 1
The system deduplicates webhook events using issue URL + event timestamp. Processing the same event twice produces no side effects (no duplicate PRs, no duplicate comments).

### REQ-03: Fresh Workspace Isolation
**Category:** Table Stakes | **Complexity:** Low | **Phase:** 1
Each job gets a fresh clone of the target repository in a temporary directory. No state persists between jobs. Workspaces are cleaned up after job completion or failure.

### REQ-04: Configurable Target Repository
**Category:** Table Stakes | **Complexity:** Low | **Phase:** 1
The target repository URL, branch, label, and credentials are configurable via environment variables or config file. Not hardcoded to a single repo.

### REQ-05: Async Job Execution
**Category:** Table Stakes | **Complexity:** Medium | **Phase:** 1
Webhook handler enqueues work and returns immediately. Heavy processing (clone, LLM, tests, PR) runs asynchronously. Job state is tracked (queued, running, completed, failed).

### REQ-06: Structured Logging
**Category:** Table Stakes | **Complexity:** Low | **Phase:** 1
All operations produce structured (JSON) log output with correlation IDs linking webhook event → job → actions. Issue number and job ID included in every log entry.

### REQ-07: Issue Analysis via LLM
**Category:** Table Stakes | **Complexity:** Medium | **Phase:** 2
The system uses magentic to analyze GitHub issue title, body, and comments. Extracts: what needs to change, which files are affected, acceptance criteria. Produces structured analysis for code generation.

### REQ-08: LLM Code Generation
**Category:** Table Stakes | **Complexity:** Medium | **Phase:** 2
The system uses magentic to generate code changes based on issue analysis. Loads relevant source files as context with token budgeting. Applies changes to the workspace. Uses temperature=0 for deterministic output.

### REQ-09: Context Budget Management
**Category:** Table Stakes | **Complexity:** Medium | **Phase:** 2
LLM calls track token usage against model context limits. Files are selected by relevance and pruned to fit within budget. Context overflow is detected and handled gracefully (reduce scope, not silently truncate).

### REQ-10: PR Creation with Explanation
**Category:** Table Stakes | **Complexity:** Low | **Phase:** 2
The system creates a GitHub PR with: conventional commit messages, structured description (summary, approach, testing notes), issue cross-reference (Fixes #N), and co-author attribution.

### REQ-11: Multi-File Changes
**Category:** Table Stakes | **Complexity:** Medium | **Phase:** 2
The system can modify, create, or delete multiple files in a single PR. Changes are coordinated (e.g. new function + import + test).

### REQ-12: Test Execution
**Category:** Table Stakes | **Complexity:** Low | **Phase:** 3
The system runs the target repo's test suite (or relevant subset) via subprocess with configurable timeout. Captures pass/fail status, stdout, stderr, and exit code.

### REQ-13: Iterative Refinement
**Category:** Differentiator | **Complexity:** High | **Phase:** 3
On test failure, the system feeds error output back to the LLM and regenerates code. Retries up to N times (configurable). Each iteration includes previous error context. Stops when tests pass or max retries reached.

### REQ-14: Error Recovery and Notification
**Category:** Table Stakes | **Complexity:** Medium | **Phase:** 3
On permanent failure, the system: comments on the GitHub issue with error details, opens a draft PR with partial work (if any), marks the job as failed. Transient errors (API timeout, rate limit) retry with exponential backoff.

### REQ-15: Basic Security — Path Restrictions
**Category:** Table Stakes | **Complexity:** Low | **Phase:** 2
Generated code changes are restricted to allowed paths. Modifications to security-sensitive files (.github/workflows, .env, credentials) are flagged or blocked. Issue content is treated as untrusted input.

### REQ-16: Self-Modification
**Category:** Differentiator | **Complexity:** High | **Phase:** 4
Booty can process issues against its own repository. The same pipeline (analyze → generate → test → PR) works when the target repo is Booty itself. Self-PRs follow the same quality gates as external repos.

### REQ-17: Deterministic Configuration
**Category:** Table Stakes | **Complexity:** Low | **Phase:** 1
LLM temperature, model selection, timeout values, retry limits, and all operational parameters are configurable. Defaults are deterministic (temperature=0, sorted file ordering).

## v2 Scope (Deferred)

### REQ-V2-01: Docker Sandboxing
Run generated code and tests inside Docker containers for stronger isolation.

### REQ-V2-02: Quality Gates (Linters/Security)
Run linters, formatters, type checkers, and security scanners before tests. Block PR if quality gates fail.

### REQ-V2-03: Multi-Agent Architecture
Add Verifier, Planner, Architect agents with coordination protocols.

### REQ-V2-04: Deep Codebase Understanding
Semantic code analysis: call graphs, data flow, dependency mapping beyond simple file reading.

### REQ-V2-05: Learning from Feedback
Incorporate PR review comments and merge/reject signals into future agent behavior.

### REQ-V2-06: GitHub App Authentication
Use GitHub App installation tokens (scoped, auto-expiring) instead of PATs.

### REQ-V2-07: Test Selection Optimization
Run only tests related to changed files instead of full suite.

## Out of Scope

- Custom UI or dashboard (GitHub is the interface)
- Fine-tuned or custom-hosted LLM models
- Auto-merge without human approval
- Deployment automation (stops at PR)
- Real-time chat interface
- Slack/Discord integrations
- Issue triage or labeling
- Cross-repo changes in a single PR
- Production deployment infrastructure

## Traceability

| Requirement | Research Source | Phase |
|-------------|---------------|-------|
| REQ-01 | ARCHITECTURE (Webhook Gateway), PITFALLS (#3 timeout) | 1 |
| REQ-02 | PITFALLS (#3 retry storm), FEATURES (idempotency) | 1 |
| REQ-03 | ARCHITECTURE (workspace isolation), PITFALLS (#4 state) | 1 |
| REQ-04 | FEATURES (configurable repos), PROJECT.md | 1 |
| REQ-05 | ARCHITECTURE (async pattern), PITFALLS (#3 timeout) | 1 |
| REQ-06 | PITFALLS (#15 logging), ARCHITECTURE (correlation IDs) | 1 |
| REQ-07 | ARCHITECTURE (Issue Analyzer), FEATURES (read codebase) | 2 |
| REQ-08 | ARCHITECTURE (Code Generator), FEATURES (code gen) | 2 |
| REQ-09 | PITFALLS (#1 context blindness), SUMMARY (cross-cutting) | 2 |
| REQ-10 | FEATURES (PR with explanation), ARCHITECTURE (Git Operator) | 2 |
| REQ-11 | FEATURES (multi-file changes) | 2 |
| REQ-12 | FEATURES (test execution), ARCHITECTURE (Test Runner) | 3 |
| REQ-13 | FEATURES (iterative refinement), ARCHITECTURE (retry loop) | 3 |
| REQ-14 | PITFALLS (#10 failure recovery), FEATURES (error recovery) | 3 |
| REQ-15 | PITFALLS (#5 prompt injection), SUMMARY (security) | 2 |
| REQ-16 | FEATURES (self-modification), PROJECT.md (self-managing) | 4 |
| REQ-17 | PITFALLS (#6 determinism, #16 hardcoded config) | 1 |

---
*Generated: 2026-02-14 from research synthesis*
