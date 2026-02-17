# Phase 43: Dedup Alignment — Research

## RESEARCH COMPLETE

**Gathered:** 2026-02-17
**Status:** Ready for planning

---

## Executive Summary

Phase 43 aligns PR agent dedup keys to `(repo_full_name, pr_number, head_sha)` and documents issue agent dedup keys. VerifierQueue and SecurityQueue currently use `(pr_number, head_sha)` only — a multi-repo collision risk. ReviewerQueue already uses the correct key. Implementation is a straightforward signature change plus router call-site updates.

---

## Current State

### PR Agent Dedup Keys

| Queue | Current signature | Target | Status |
|-------|-------------------|--------|--------|
| VerifierQueue | `is_duplicate(pr_number, head_sha)` | `(repo_full_name, pr_number, head_sha)` | **Needs update** |
| SecurityQueue | `is_duplicate(pr_number, head_sha)` | `(repo_full_name, pr_number, head_sha)` | **Needs update** |
| ReviewerQueue | `is_duplicate(repo_full_name, pr_number, head_sha)` | — | ✓ Already correct |

### VerifierQueue / SecurityQueue Implementation

- **File:** `src/booty/verifier/queue.py`, `src/booty/security/queue.py`
- **_dedup_key:** `f"{pr_number}:{head_sha}"` — no repo
- **Callers:** Router `_route_pull_request` at lines 311 (verifier), 368 (security)
- **Job shapes:** VerifierJob and SecurityJob both have `owner`, `repo_name` — can derive `repo_full_name` via `f"{job.owner}/{job.repo_name}"` or pass from router

### ReviewerQueue (Reference Implementation)

- **File:** `src/booty/reviewer/queue.py`
- **_dedup_key:** `f"{repo_full_name}:{pr_number}:{head_sha}"`
- **enqueue:** Internally derives `repo_full_name` from job; uses it for `is_duplicate`, `mark_processed`, `request_cancel`

### Router Call Sites

| Agent | Call | Line |
|-------|------|------|
| Verifier | `verifier_queue.is_duplicate(internal.pr_number, internal.head_sha)` | 311 |
| Verifier | `verifier_queue.enqueue(job)` → internally `mark_processed(job.pr_number, job.head_sha)` | 335 |
| Reviewer | `reviewer_queue.is_duplicate(internal.full_name, internal.pr_number, internal.head_sha)` | 345 |
| Security | `security_queue.is_duplicate(internal.pr_number, internal.head_sha)` | 368 |
| Security | `security_queue.enqueue(sec_job)` → internally `mark_processed(job.pr_number, job.head_sha)` | 386 |

**Key:** Router has `internal.full_name` (repo_full_name) for all PR events. Verifier and Security just need the router to pass it into the new signatures.

### Issue Agent Dedup (DEDUP-02 — Document Only)

| Agent | Current key | Documentation |
|-------|-------------|---------------|
| Planner | `planner_is_duplicate(delivery_id)` | `(repo, delivery_id)` — delivery_id is globally unique per webhook; repo implicit |
| Builder (JobQueue) | `is_duplicate(delivery_id)`, `has_issue_in_queue(repo_url, issue_number)` | Issue-driven: `(repo, delivery_id)`; plan-driven: `(repo, plan_hash)` (Phase 44) |
| Architect | — | TBD Phase 44 |

Per 43-CONTEXT: Document dedup keys; no code changes for Planner/Builder. Architect reserved.

---

## Key Findings

### 1. Single Atomic Change

- Update VerifierQueue and SecurityQueue `_dedup_key`, `is_duplicate`, `mark_processed`, `enqueue` to accept `repo_full_name` as first arg
- Mirror ReviewerQueue pattern exactly
- Update router to pass `internal.full_name` to all three queues
- No external API; all callers are internal (router)

### 2. Job Shapes Already Have Repo Info

- VerifierJob: `owner`, `repo_name` → `f"{owner}/{repo_name}"`
- SecurityJob: same
- Enqueue can derive repo_full_name from job; `is_duplicate` and `mark_processed` are called *before* enqueue from router — router must pass `internal.full_name`

### 3. Verifier Logic Inconsistency

- Verifier: `if verifier_queue.is_duplicate(...)` → skip (don't enqueue)
- Reviewer: `if not reviewer_queue.is_duplicate(...)` → enqueue (positive check)
- Security: `if not security_queue.is_duplicate(...)` → enqueue
- Minor: Verifier logs "verifier_already_processed" and continues; Reviewer/Security check before creating job. All equivalent; keep as-is for consistency with current flow.

### 4. No Tests for Dedup Signatures

- No unit tests that assert `is_duplicate(repo, pr, sha)` for Verifier/Security
- Reviewer has tests; add Verifier/Security tests or extend existing queue tests

### 5. Transition Behavior (from 43-CONTEXT)

- **Rollout:** Single atomic change — one PR
- **In-flight:** Ignore (in-memory; restart clears)
- **Missing repo:** Hard fail — new API requires repo; no fallback

---

## Files to Modify

1. **src/booty/verifier/queue.py** — Add repo_full_name to _dedup_key, is_duplicate, mark_processed, enqueue
2. **src/booty/security/queue.py** — Same
3. **src/booty/router/router.py** — Pass internal.full_name to verifier/security is_duplicate calls; enqueue uses job fields (queue derives or we pass—simplest: queue uses job.owner/repo_name in enqueue; for is_duplicate the router has internal.full_name)
4. **docs/** — Add DEDUP-KEYS.md or section in capabilities-summary documenting all agent dedup keys

---

## Recommendations for Planning

1. **Plan 43-01:** VerifierQueue + SecurityQueue signature changes + router updates (single wave; tightly coupled)
2. **Plan 43-02:** Documentation for issue agent dedup keys (DEDUP-02)
3. **Optional:** Extend queue tests to assert repo-scoped dedup (recommended but not blocking)

---

## Open Decisions (Claude's Discretion)

- Exact doc placement (new file vs. existing docs)
- Whether to add unit tests for VerifierQueue/SecurityQueue with repo in key
