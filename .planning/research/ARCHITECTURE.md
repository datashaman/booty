# Architecture Research: AI Coding Agent Systems

**Domain:** Webhook-triggered, repo-cloning, LLM-powered builder agents
**Researched:** 2026-02-14
**Confidence:** MEDIUM (based on established patterns from GitHub bots, LLM agents, CI/CD systems)

## Recommended Architecture

### Overview

Booty follows an **async event-driven pipeline** architecture. The webhook handler is a thin gateway that enqueues jobs; all heavy processing happens asynchronously. Each job gets a fresh workspace and progresses through a deterministic pipeline: clone → analyze → generate → test → commit → PR.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   GitHub     │────▶│   Webhook    │────▶│     Event        │
│  (webhook)   │     │   Gateway    │     │   Orchestrator   │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                    ┌──────────────────────────────┘
                    ▼
              ┌───────────┐     ┌──────────────┐
              │ Repository │────▶│    Issue      │
              │  Manager   │     │   Analyzer    │
              └───────────┘     └──────┬───────┘
                                       │
                                       ▼
                                ┌──────────────┐
                                │    Code      │
                                │  Generator   │
                                └──────┬───────┘
                                       │
                                       ▼
                                ┌──────────────┐
                                │    Test      │◀──┐
                                │   Runner     │───┘ retry loop
                                └──────┬───────┘
                                       │
                                       ▼
                                ┌──────────────┐
                                │     Git      │
                                │   Operator   │
                                └──────────────┘
```

## Component Boundaries

### 1. Webhook Gateway
**Responsibility:** Receive HTTP requests, validate signatures, route events.

- Listens on `/webhook/github` endpoint
- Verifies `X-Hub-Signature-256` using HMAC-SHA256
- Filters events: only `issues` with action `labeled` and matching label
- Returns 200 OK immediately after enqueuing
- **Does NOT** do any processing — just validation and routing

**Interfaces:**
- IN: HTTP POST from GitHub
- OUT: Job enqueued to Event Orchestrator

**Technology:** FastAPI endpoint

### 2. Event Orchestrator
**Responsibility:** Job lifecycle management, retry logic, status tracking.

- Receives jobs from webhook gateway
- Manages job state machine: `queued → running → completed/failed`
- Handles retries with exponential backoff
- Ensures idempotency (deduplication by issue URL + event timestamp)
- Reports status back to GitHub (commit status API or issue comments)

**Interfaces:**
- IN: Job from Webhook Gateway
- OUT: Dispatches to Repository Manager, tracks completion

**Technology:** asyncio tasks (v1), task queue like Celery/RQ (v2)

### 3. Repository Manager
**Responsibility:** Clone repos, manage workspaces, handle credentials.

- Creates fresh clone per task in temp directory
- Configures git credentials for push access
- Creates feature branch from default branch
- Handles cleanup after job completion
- Shallow clone option for large repos

**Interfaces:**
- IN: Repo URL + credentials from config
- OUT: Workspace path with cloned repo ready for use

**Technology:** GitPython + tempfile

### 4. Issue Analyzer
**Responsibility:** Extract requirements from GitHub issue using LLM.

- Reads issue title, body, comments, labels
- Uses LLM to extract: what needs to change, acceptance criteria, affected files
- Identifies relevant files in the codebase for context
- Produces structured task description for Code Generator

**Interfaces:**
- IN: GitHub issue data + workspace path
- OUT: Structured analysis (files to modify, changes needed, constraints)

**Technology:** magentic @prompt functions + PyGithub

### 5. Code Generator
**Responsibility:** Generate code changes using LLM.

- Receives structured analysis from Issue Analyzer
- Loads relevant source files as context (with token budgeting)
- Uses LLM to generate file modifications
- Applies changes to workspace
- Runs formatters/linters on generated code

**Interfaces:**
- IN: Structured analysis + workspace with source files
- OUT: Modified files in workspace

**Technology:** magentic @prompt functions

### 6. Test Runner
**Responsibility:** Execute tests, collect results, provide feedback.

- Runs test suite (or relevant subset) via subprocess
- Captures stdout/stderr and exit code
- Parses test results for pass/fail details
- On failure: feeds error output back to Code Generator for retry
- Enforces timeout limits

**Interfaces:**
- IN: Workspace with modified code
- OUT: Test results (pass/fail, details, coverage)
- FEEDBACK: Error details back to Code Generator on failure

**Technology:** subprocess.run with timeout + pytest output parsing

### 7. Git Operator
**Responsibility:** Commit changes, push branch, create PR.

- Creates meaningful commit messages (conventional commits format)
- Commits with co-author attribution
- Pushes feature branch to remote
- Creates PR via GitHub API with structured description
- Links PR to originating issue

**Interfaces:**
- IN: Workspace with committed changes + issue reference
- OUT: PR URL

**Technology:** GitPython + PyGithub

### 8. Configuration Store
**Responsibility:** Manage settings, credentials, per-repo configuration.

- Target repo configurations (URL, branch, labels)
- LLM settings (model, temperature, token limits)
- GitHub credentials (App installation tokens or PATs)
- Webhook secret
- Timeout and retry settings

**Interfaces:**
- IN: Config files (.env, config.yaml) + environment variables
- OUT: Configuration values for all components

**Technology:** python-dotenv + Pydantic settings

## Data Flow

### Happy Path
```
1. GitHub sends webhook event (issue labeled with `agent:builder`)
2. Webhook Gateway validates signature, checks event type
3. Gateway enqueues job with issue data → returns 200 OK
4. Orchestrator picks up job, sets status to "running"
5. Repository Manager clones target repo to /tmp/booty-{job_id}/
6. Issue Analyzer reads issue + codebase, produces structured analysis
7. Code Generator loads relevant files, generates changes via LLM
8. Test Runner executes tests in workspace
   - If FAIL: feed errors back to Code Generator (step 7), retry up to N times
   - If PASS: continue
9. Git Operator commits, pushes branch, creates PR
10. Orchestrator marks job complete, comments on issue with PR link
11. Workspace cleaned up
```

### Error Handling Flow
```
At any step:
├─ Transient error (API timeout, rate limit)
│   └─ Retry with exponential backoff (max 3 attempts)
├─ LLM error (context overflow, invalid response)
│   └─ Reduce context, retry with simplified prompt
├─ Test failure (after max retries)
│   └─ Open PR as draft with failure details, comment on issue
├─ Fatal error (invalid config, auth failure)
│   └─ Comment on issue with error, mark job failed, alert
└─ All paths: log with correlation ID, clean up workspace
```

## Architectural Patterns

### Pattern: Async Job Processing
Webhooks must return fast. All heavy work happens async.
```python
@app.post("/webhook/github")
async def webhook(request: Request):
    verify_signature(request)
    payload = await request.json()
    job_id = enqueue_job(payload)  # Returns immediately
    return {"status": "accepted", "job_id": job_id}
```

### Pattern: Workspace Isolation
Every job gets a fresh, isolated workspace.
```python
workspace = tempfile.mkdtemp(prefix=f"booty-{job_id}-")
try:
    repo = Repo.clone_from(url, workspace, depth=1)
    # ... all work happens in workspace ...
finally:
    shutil.rmtree(workspace)
```

### Pattern: Retry with Feedback
Test failures feed back into code generation.
```python
for attempt in range(max_retries):
    generate_code(analysis, workspace, previous_errors=errors)
    result = run_tests(workspace)
    if result.passed:
        break
    errors = result.error_output
```

### Pattern: Context Budgeting
Never send more tokens than the model can handle.
```python
budget = model_context_limit - system_prompt_tokens - output_reserve
file_tokens = estimate_tokens(relevant_files)
if file_tokens > budget:
    relevant_files = prune_to_budget(relevant_files, budget)
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Do This Instead |
|-------------|-------------|-----------------|
| Synchronous webhook processing | Timeouts, duplicate jobs, delivery failures | Enqueue + return 200 immediately |
| Shared workspace between jobs | State leakage, security risks, race conditions | Fresh clone per task |
| Dumping entire codebase to LLM | Context overflow, degraded quality | Smart file selection with token budgeting |
| Global error handlers | Masks root causes, loses context | Per-component error handling with correlation IDs |
| Monolithic agent function | Untestable, unmaintainable | Separate components with clear interfaces |
| Hardcoded prompts in source | Can't iterate on prompts easily | Prompt files, templates, versioning |

## Build Order

Based on dependency analysis, components should be built in this order:

### Tier 1: Foundation (no dependencies, build first)
1. **Configuration Store** — Everything needs config
2. **Webhook Gateway** — Entry point, can test independently

### Tier 2: Core Operations (needs config)
3. **Repository Manager** — Needs config for credentials/URLs
4. **Test Runner** — Needs workspace from repo manager

### Tier 3: LLM Integration (needs repo manager + config)
5. **Issue Analyzer** — Needs repo workspace + LLM client
6. **Code Generator** — Needs repo workspace + LLM client

### Tier 4: Output (needs everything above)
7. **Git Operator** — Needs workspace + config + GitHub client

### Tier 5: Orchestration (ties it all together)
8. **Event Orchestrator** — Coordinates all components, built last

### Recommended Phase Structure
```
Phase 1: Tiers 1-2 (webhook + repo clone + config + test running)
Phase 2: Tier 3 (LLM integration: analyze issues, generate code)
Phase 3: Tiers 4-5 (git operations + orchestration = end-to-end)
```

## Security Boundaries

| Boundary | Threat | Mitigation |
|----------|--------|------------|
| Webhook input | Spoofed events | HMAC signature verification |
| Issue content | Prompt injection | Treat as untrusted, structured prompts |
| Generated code | Malicious output | Path restrictions, sandboxed execution |
| Credentials | Exposure | Environment variables, never in code/logs |
| Workspace | File system access | Temp directories, cleanup after job |
| LLM API | Key theft | Rotate keys, monitor usage |

## Scalability Considerations (Future)

- **v1:** Single process, asyncio tasks, one job at a time
- **v2:** Task queue (Celery/RQ), concurrent jobs, job persistence
- **v3:** Container-per-job isolation, horizontal scaling, job distribution

---

*Research completed: 2026-02-14*
*Based on: GitHub App/Bot patterns (Probot, Dependabot, Renovate), LLM agent architectures, event-driven design*
*Confidence: MEDIUM*
