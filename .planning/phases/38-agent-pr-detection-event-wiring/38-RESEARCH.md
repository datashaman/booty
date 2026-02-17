# Phase 38: Agent PR Detection + Event Wiring - Research

**Domain:** pull_request webhook, Reviewer queue, agent PR filtering, dedup/cancel

## Summary

Phase 38 wires the Reviewer into the pull_request webhook. Reviewer runs only for agent PRs (opened, synchronize, reopened). It mirrors Verifier/Security patterns with three key differences: (1) agent PR filter only, (2) repo-inclusive dedup key, (3) cooperative cancel on new SHA. The worker loads `.booty.yml` and no-ops when Reviewer is disabled per repo.

## Existing Patterns

### pull_request Webhook Flow (webhooks.py:253–367)

```
event_type == "pull_request"
  → action in (opened, synchronize, reopened)
  → Extract: owner, repo_name, pr_number, head_sha, head_ref, repo_url, installation_id, labels
  → is_agent_pr = TRIGGER_LABEL in labels OR user.type=="Bot" OR head_ref.startswith("agent/issue-")
  → Verifier enqueue (if verifier_ok, !is_duplicate)
  → Security enqueue (if security_ok, !is_duplicate)
  → Return 202
```

**Early return:** If neither verifier_ok nor security_ok, return `verifier_and_security_disabled`. Must extend to include reviewer_ok.

### Agent PR Detection (webhooks.py:286–291)

Same logic for Verifier, Security, Reviewer:
```python
is_agent_pr = (
    settings.TRIGGER_LABEL in labels
    or pr.get("user", {}).get("type") == "Bot"
    or head_ref.startswith("agent/issue-")
)
```

### VerifierQueue / SecurityQueue Pattern

- `is_duplicate(pr_number, head_sha)` — dedup key `pr_number:head_sha`
- `enqueue(job)` — returns False if duplicate; marks processed before put
- `worker(process_fn)` — consumes jobs, calls process_fn
- `start_workers`, `shutdown`

Verifier and Security use `pr_number:head_sha`. Phase 38 CONTEXT specifies Reviewer dedup key: `{repo_full_name}:{pr_number}:{head_sha}` for multi-repo safety.

### Cancel Semantics (from CONTEXT)

- **Cooperative cancel:** No process kill. Worker checks cancel flag between phases.
- **On new SHA:** Mark prior run cancelled, enqueue new run.
- **Cancel check points:** Before LLM call, before posting comment, before finalizing check.
- **Conclusion:** Use `cancelled` or neutral per GitHub API when run is superseded.

VerifierQueue does not implement cancel—it only dedups. For Reviewer, we need:
1. Track in-flight jobs by `repo:pr_number` (not sha)
2. When new SHA for same PR arrives, set cancel flag for prior job
3. Worker checks flag at phase boundaries and exits early (conclusion: cancelled)

## Phase 38 Additions

### ReviewerQueue

- Dedup key: `{repo_full_name}:{pr_number}:{head_sha}` (e.g. `owner/repo:123:abc123`)
- Cancel: `request_cancel(repo_full_name, pr_number)` — marks in-flight job for same PR as cancelled
- Worker passes job to `process_reviewer_job`; job carries `cancelled: asyncio.Event` or callback to check
- On enqueue with new SHA for same PR: call `request_cancel(repo, pr_number)` then enqueue new job

### ReviewerJob

```python
@dataclass
class ReviewerJob:
    job_id: str
    owner: str
    repo_name: str
    pr_number: int
    head_sha: str
    head_ref: str
    repo_url: str
    installation_id: int
    payload: dict
    is_agent_pr: bool  # Always True when enqueued (webhook filters)
```

### Webhook Changes

1. Add `reviewer_queue` to app.state (lifespan), `reviewer_ok` = reviewer_queue exists and verifier_enabled (same App)
2. Extend early return: `if not verifier_ok and not security_ok and not reviewer_ok`
3. **Reviewer enqueue:** Only when `reviewer_ok and is_agent_pr`:
   - Dedup key `repo_full_name:pr_number:head_sha`
   - Request cancel for prior job on same PR (if new SHA)
   - Enqueue ReviewerJob

### Worker Flow (Phase 38 Stub)

Phase 38 is event plumbing only. The runner creates check lifecycle and can stub the outcome:

1. `create_reviewer_check_run(queued)` — output title "Booty Reviewer"
2. `edit_check_run(in_progress)` — output title "Booty Reviewer"
3. Load `.booty.yml` via get_verifier_repo + get_contents
4. `get_reviewer_config(booty_config)` — if None, no-op (no check completion, no comment)
5. If enabled: Phase 39 will add LLM. For Phase 38 stub: `edit_check_run(completed, conclusion=success, output title "Reviewer approved")`

REV-05 titles: Queued/In progress = "Booty Reviewer"; Success = "Reviewer approved" or "Reviewer approved with suggestions"; Failure = "Reviewer blocked". Phase 38 stub uses "Reviewer approved".

### Config Loading

Worker fetches `.booty.yml` from repo at head_sha. No config at webhook time (keeps webhook fast).

## Files to Create/Modify

| File | Action |
|------|--------|
| src/booty/reviewer/job.py | Create ReviewerJob dataclass |
| src/booty/reviewer/queue.py | Create ReviewerQueue (dedup, cancel) |
| src/booty/reviewer/runner.py | Create process_reviewer_job (stub) |
| src/booty/webhooks.py | Add reviewer enqueue in pull_request block |
| src/booty/main.py | Add reviewer_queue, _process_reviewer_job, lifespan |
| src/booty/config.py | Add REVIEWER_WORKER_COUNT (optional, default 2) |

## Open Decisions

1. **reviewer_enabled at webhook:** Use same as verifier_enabled (App credentials). Worker no-ops when repo config disables Reviewer.
2. **Cancel storage:** Queue tracks `_in_flight: dict[tuple[str,int], asyncio.Event]` — (repo, pr_number) → Event. When new SHA enqueued, set Event. Worker holds reference and checks `event.is_set()`.
3. **GitHub check conclusion for cancelled:** `conclusion="cancelled"` if supported; else `conclusion="skipped"` or neutral. Check GitHub Checks API docs for `cancelled`.

## Sources

- src/booty/webhooks.py (pull_request block)
- src/booty/verifier/queue.py, verifier/job.py, verifier/runner.py
- src/booty/security/queue.py, security/job.py
- src/booty/github/checks.py (create_reviewer_check_run, edit_check_run)
- src/booty/main.py (lifespan)
- .planning/phases/38-agent-pr-detection-event-wiring/38-CONTEXT.md

---
*Research complete — ready for planning*
