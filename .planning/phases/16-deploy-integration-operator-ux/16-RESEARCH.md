# Phase 16: Deploy Integration & Operator UX - Research

**Researched:** 2026-02-16
**Domain:** GitHub workflow_dispatch, commit status, workflow_run observation, PyGithub
**Confidence:** HIGH

## Summary

Phase 16 adds deploy execution and operator feedback: (1) trigger deploy via workflow_dispatch with sha input, (2) HOLD/ALLOW commit status on merge commit, (3) observe deploy workflow_run completion to update release state, (4) create/append GitHub issues on deploy failure. The codebase already has PyGithub, workflow_run webhook, release state store, and deploy workflow with sha input. Standard approach: extend webhook with a second workflow_run branch for deploy workflow completion; add deploy trigger and UX modules; use `repo.get_workflow(filename).create_dispatch()` and `repo.get_commit(sha).create_status()`.

**Primary recommendation:** Use `gh_repo.get_workflow(deploy_workflow_name).create_dispatch(ref=config.deploy_workflow_ref, inputs={"sha": head_sha})`; `repo.get_commit(sha).create_status(state, target_url, description, context="booty/release-governor")`; add workflow_run branch filtering by `deploy_workflow_name` for deploy outcome observation.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyGithub | (existing) | workflow_dispatch, commit status, create_issue | Already in project; supports all needed APIs |
| FastAPI | (existing) | Webhook routes | Project standard |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| structlog | Logging | Project standard |
| Python stdlib | datetime, json | State updates, issue body formatting |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyGithub | gh CLI / raw REST | PyGithub already used; no subprocess |
| commit status | Checks API | Status is simpler; CONTEXT.md chose status |
| workflow_run webhook | Polling | CONTEXT: webhook preferred, polling fallback |

## Architecture Patterns

### Recommended Project Structure
```
src/booty/release_governor/
├── handler.py       # handle_workflow_run (verification) - extend orchestration
├── deploy.py        # dispatch_deploy, post_deploy_ux, observe_deploy_outcome
├── ux.py            # post_hold_status, post_allow_status, build_how_to_unblock
├── failure_issues.py # create_or_append_deploy_failure_issue
├── store.py         # (existing) append_deploy_to_history, save production_sha
└── ...
```

### Pattern 1: workflow_dispatch with sha Input
**What:** Trigger deploy workflow via GitHub Actions API with sha input.
**When to use:** On ALLOW decision, only for head_sha (GOV-18).
**Example:**
```python
# Source: Context7 PyGithub, GitHub REST API
gh = Github(token)
repo = gh.get_repo(repo_full_name)
workflow = repo.get_workflow(config.deploy_workflow_name)  # e.g. "deploy.yml"
workflow.create_dispatch(
    ref=config.deploy_workflow_ref,
    inputs={"sha": head_sha}
)
# Returns 204 No Content; no run ID in response — get from subsequent workflow_run webhook
```

**Note:** API returns 204 with no body. Workflow run link comes from workflow_run webhook when deploy starts; for ALLOW status target_url use GitHub Actions runs list or wait for first workflow_run event.

### Pattern 2: Commit Status for HOLD/ALLOW
**What:** Create commit status on merge commit with context `booty/release-governor`.
**When to use:** After every decision (HOLD or ALLOW).
**Example:**
```python
# Source: Context7 PyGithub
repo.get_commit(sha).create_status(
    state="success",   # ALLOW: success; HOLD: failure
    target_url="https://github.com/owner/repo/actions/runs/123",
    description="Decision, SHA, Risk, Reason",
    context="booty/release-governor"
)
```

**State mapping:** ALLOW → `success`, HOLD → `failure`. Description truncated to 140 chars; full "how to unblock" via target_url (CONTEXT: link to Actions run or docs).

### Pattern 3: workflow_run for Deploy Outcome
**What:** Receive workflow_run when deploy workflow completes; filter by workflow name.
**Relevant fields:**
- `action`: "completed"
- `workflow_run.conclusion`: "success" | "failure" | "cancelled" | ...
- `workflow_run.name`: "Deploy" (or deploy_workflow_name)
- `workflow_run.head_sha`: SHA deployed
- `workflow_run.html_url`: Link to run
- `workflow_run.id`: Run ID

**When to use:** Add second branch in webhook: if `workflow_name == deploy_workflow_name` and `action == "completed"`, handle deploy outcome (update state, create issue on failure).

### Pattern 4: Create/Append Deploy Failure Issue
**What:** Create issue with labels `deploy-failure`, `severity:high`, failure-type label.
**Example:**
```python
# Source: Context7 PyGithub
repo.create_issue(
    title=f"Deploy failure: {sha[:7]}",
    body=body_with_link_and_summary,
    labels=["deploy-failure", "severity:high", "deploy:health-check-failed"]
)
# Append: find open issue by label + SHA, add comment
```

**Append strategy (CONTEXT):** New issue per SHA; append to same SHA's issue if rapid retry. Use labels + search or in-memory cache for "recent failure for this SHA".

### Anti-Patterns to Avoid
- **Don't deploy non-head_sha:** GOV-18 — only dispatch when decision.sha == workflow_run.head_sha
- **Don't use issue comments for HOLD:** CONTEXT chose commit status only
- **Don't poll by default:** Use workflow_run webhook; add polling only as fallback if events missed

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Workflow trigger | Custom REST | repo.get_workflow().create_dispatch() | Handles auth, retries |
| Commit status | Raw API | repo.get_commit().create_status() | PyGithub abstracts |
| Issue creation | Raw API | repo.create_issue() | Label handling, retries |
| workflow_run routing | Single handler | Branch by workflow name | Verification vs deploy are different flows |

## Common Pitfalls

### Pitfall 1: workflow_dispatch Returns No Run ID
**What goes wrong:** API returns 204, no body; can't get run URL immediately.
**Why it happens:** Design of GitHub Actions API.
**How to avoid:** Use workflow_run webhook (in_progress or completed) to get run URL; for ALLOW status, post "Triggered deploy" with placeholder or wait for first workflow_run event; or use generic runs list URL.

### Pitfall 2: Status Description Truncation
**What goes wrong:** Description limited to 140 characters.
**Why it happens:** GitHub API limit.
**How to avoid:** Put full "how to unblock" in target_url; keep description to "HOLD: first_deploy_required — add approval" style.

### Pitfall 3: workflow_run Payload Ambiguity
**What goes wrong:** Both verification and deploy send workflow_run; must distinguish.
**Why it happens:** Same event type for all workflow completions.
**How to avoid:** Filter by `workflow_run.name` — verification_workflow_name vs deploy_workflow_name.

### Pitfall 4: Double Processing
**What goes wrong:** Idempotency: same deploy outcome processed twice.
**How to avoid:** Use delivery_id for webhook idempotency; for deploy outcome, key by (repo, workflow_run.id) or (repo, head_sha, conclusion) with short TTL to dedupe retries.

## Code Examples

### Dispatch Deploy (ALLOW)
```python
workflow = gh_repo.get_workflow(config.deploy_workflow_name)
workflow.create_dispatch(
    ref=config.deploy_workflow_ref,
    inputs={"sha": head_sha}
)
```

### Post HOLD Status
```python
repo.get_commit(head_sha).create_status(
    state="failure",
    target_url=how_to_unblock_url,
    description=f"HOLD: {reason} — {sha[:7]}",
    context="booty/release-governor"
)
```

### Post ALLOW Status (after dispatch)
```python
repo.get_commit(head_sha).create_status(
    state="success",
    target_url=workflow_run_url,
    description=f"Triggered: deploy workflow run",
    context="booty/release-governor"
)
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Push-to-main deploy | workflow_dispatch only (Governor triggers) | Phase 14/15 |
| No operator feedback | commit status booty/release-governor | Phase 16 |
| Deploy failure silent | GitHub issue with labels | Phase 16 |

## Open Questions

1. **target_url for "how to unblock"**
   - CONTEXT: Planner's discretion — Actions run vs docs.
   - Recommendation: Link to Actions run (filter by workflow) when available; fallback to docs/release-governor.md.

2. **Append vs new issue thresholds**
   - CONTEXT: Hybrid — new per SHA; append for rapid retries.
   - Recommendation: Append if same SHA failed in last 30 min; else new issue.

3. **Reconciliation cadence**
   - CONTEXT: Periodic reconciliation if events missed.
   - Recommendation: Defer to later iteration; webhook-first is sufficient for v1.4.

## Sources

### Primary (HIGH confidence)
- Context7 PyGithub - workflow create_dispatch, commit status, create_issue
- GitHub REST API docs - workflow_dispatch, statuses, workflow_run payload

### Secondary (MEDIUM confidence)
- Project .github/workflows/deploy.yml - sha input, DEPLOY_SHA
- Phase 15 RESEARCH, webhooks.py - workflow_run filtering pattern

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PyGithub verified, deploy workflow exists
- Architecture: HIGH - Patterns from Context7, CONTEXT.md constraints
- Pitfalls: HIGH - Documented in GitHub docs

**Research date:** 2026-02-16
**Valid until:** 30 days
