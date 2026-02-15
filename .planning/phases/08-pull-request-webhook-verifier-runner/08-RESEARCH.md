# Phase 8: pull_request Webhook + Verifier Runner - Research

**Researched:** 2026-02-15
**Domain:** GitHub pull_request webhook, Verifier job orchestration, Booty existing patterns
**Confidence:** HIGH

## Summary

Phase 8 wires the Verifier into the PR lifecycle. The existing codebase provides: webhooks.py (HMAC, idempotency, issues filtering), JobQueue, prepare_workspace, execute_tests, load_booty_config, and checks.py (create_check_run, edit_check_run). The work is extending these patterns for pull_request events and adding a Verifier worker path.

**Primary recommendation:** Extend webhooks.py with a pull_request branch (opened, synchronize, reopened); add VerifierJob dataclass and verifier queue/worker; add prepare_verification_workspace (clone at head_sha); reuse execute_tests and load_booty_config. Use same JobQueue with a second worker pool for VerifierJob (or route by job type in single pool). Per 08-CONTEXT: PR-level dedup (pr_number + head_sha), cancel in-progress on new synchronize, single Verifier comment per PR on failure.

## Standard Stack

### Core (Use These)

| Library/Pattern | Purpose | Why |
|-----------------|---------|-----|
| FastAPI webhook | pull_request handling | Same endpoint as issues; branch on X-GitHub-Event |
| JobQueue | Verifier job enqueue | Same pattern as Builder jobs |
| prepare_workspace pattern | Clone at ref | Verifier needs variant: clone + checkout head_sha |
| execute_tests | Run tests | Direct reuse from test_runner |
| load_booty_config | Config from workspace | Direct reuse from test_runner |
| checks.py | create_check_run, edit_check_run | Phase 7 delivers; App auth |
| PyGithub | PR labels, comments, promote | Existing; add agent:builder label |

### Don't Add

| Avoid | Why |
|-------|-----|
| Separate webhook endpoint | One /webhooks/github; branch on event type |
| Custom clone logic | GitPython already used; prepare_workspace pattern |
| New test runner | execute_tests proven |

## Architecture Patterns

### pull_request Webhook Payload

```
payload keys:
  action: "opened" | "synchronize" | "reopened" | ...
  installation: { id: number }   # Required for checks.py get_verifier_repo
  repository: { owner: { login }, name, html_url }
  pull_request:
    number, head: { sha, ref }, base: { sha, ref }
    user: { type: "User"|"Bot", login }
    labels: [{ name: "agent:builder" }, ...]
```

Handle: `action in ("opened", "synchronize", "reopened")`.

### Verifier Job Flow

```
pull_request webhook (opened|synchronize|reopened)
  → Dedup: pr_number + head_sha (ignore duplicate commit)
  → Cancel: If in-progress Verifier for same PR, cancel it
  → Enqueue VerifierJob(owner, repo_name, pr_number, head_sha, installation_id, payload)
  → Verifier worker:
     1. create_check_run(status="queued")
     2. prepare_verification_workspace(repo_url, head_sha) → clone, checkout head_sha
     3. edit_check_run(status="in_progress")
     4. load_booty_config(workspace_path)
     5. execute_tests(config.test_command, config.timeout, workspace_path)
     6. edit_check_run(status="completed", conclusion="success"|"failure", output=...)
     7. If agent PR and failure: post PR comment (single, update/replace)
     8. If agent PR and success: promote_to_ready_for_review
```

### Project Structure

```
src/booty/
├── webhooks.py           # EXTEND: pull_request branch
├── jobs.py               # EXTEND: VerifierJob dataclass (or verifier/job.py)
├── verifier/
│   ├── __init__.py
│   ├── job.py            # VerifierJob dataclass
│   ├── runner.py         # process_verifier_job()
│   └── workspace.py      # prepare_verification_workspace (or in repositories.py)
├── repositories.py        # EXTEND or NEW: prepare_verification_workspace
├── github/
│   ├── checks.py         # existing
│   ├── comments.py      # existing; add post_verifier_failure_comment
│   └── pulls.py          # existing; promote_to_ready_for_review
└── main.py               # EXTEND: verifier queue + worker
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Clone at SHA | Custom git logic | GitPython clone + checkout | Same as prepare_workspace |
| Check lifecycle | Raw REST | checks.edit_check_run | Phase 7 delivers |
| Job routing | Custom dispatcher | Same queue + job type check in worker | Simpler |
| PR comments | Manual GraphQL | PyGithub pr.create_issue_comment | Existing pattern |

## Common Pitfalls

### Pitfall 1: Missing installation_id
**What goes wrong:** create_check_run needs installation_id; pull_request payload has it at `payload["installation"]["id"]`.
**How to avoid:** Extract from payload before enqueue; store in VerifierJob.

### Pitfall 2: Clone branch vs SHA
**What goes wrong:** Cloning default branch then checkout PR branch can fail if PR is from fork.
**How to avoid:** For same-repo PRs: clone with head.ref or fetch head_sha and checkout. Use `repo.git.fetch()` then `repo.git.checkout(head_sha)` if cloning base branch.

### Pitfall 3: Race with synchronize
**What goes wrong:** Rapid pushes → multiple Verifier runs for same PR; redundant work.
**How to avoid:** Per CONTEXT: cancel in-progress for same PR when new synchronize arrives; PR-level dedup by pr_number + head_sha.

### Pitfall 4: Builder promotes agent PRs
**What goes wrong:** Generator promotes when tests pass; Verifier should own promotion for agent PRs.
**How to avoid:** Builder never promotes agent PRs. Add agent:builder label when creating PRs; skip promotion for agent PRs (all Builder PRs are agent PRs).

## Code Examples

### prepare_verification_workspace (conceptual)

```python
@asynccontextmanager
async def prepare_verification_workspace(
    repo_url: str, head_sha: str, github_token: str = ""
) -> Workspace:
    """Clone repo and checkout head_sha. For Verifier runs."""
    temp_dir = tempfile.TemporaryDirectory(prefix="booty-verifier-")
    clone_url = repo_url.replace("https://", f"https://{github_token}@") if github_token else repo_url

    def _clone():
        r = git.Repo.clone_from(clone_url, temp_dir.name, depth=50)
        r.git.fetch("origin", head_sha)
        r.git.checkout(head_sha)
        return r

    repo = await asyncio.get_running_loop().run_in_executor(None, _clone)
    yield Workspace(path=temp_dir.name, repo=repo, branch=head_sha)
    repo.close()
    temp_dir.cleanup()
```

### Agent PR detection (from payload)

```python
def is_agent_pr(payload: dict, settings: Settings) -> bool:
    pr = payload.get("pull_request", {})
    labels = [l["name"] for l in pr.get("labels", [])]
    if settings.TRIGGER_LABEL in labels:
        return True
    if pr.get("user", {}).get("type") == "Bot":
        return True
    return False
```

## State of the Art

| Existing | Phase 8 Addition |
|----------|------------------|
| issues webhook | pull_request webhook branch |
| Job (issue-based) | VerifierJob (PR-based) |
| prepare_workspace (base + branch) | prepare_verification_workspace (head_sha) |
| process_job → Builder | process_verifier_job → Verifier |
| Builder promotes when green | Verifier promotes when green (agent PRs) |

## Open Questions

1. **Queue topology:** Same queue with type dispatch vs separate Verifier queue. CONTEXT leaves to discretion. Recommendation: same JobQueue, second worker pool with process_verifier_job; route by isinstance(job, VerifierJob) or job_type field.
2. **Cancel implementation:** Process group kill vs asyncio task cancel. Recommendation: track in-flight by pr_number; on new synchronize, set cancel flag; worker checks before long steps.

## Sources

- booty/webhooks.py, jobs.py, main.py, repositories.py
- booty/github/checks.py, pulls.py, comments.py
- booty/test_runner/executor.py, config.py
- .planning/research/ARCHITECTURE.md
- .planning/phases/07-github-app-checks/07-RESEARCH.md
- GitHub webhook payload: pull_request event, installation object

---
*Phase: 08-pull-request-webhook-verifier-runner*
*Research date: 2026-02-15*
