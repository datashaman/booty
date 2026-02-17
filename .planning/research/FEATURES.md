# Feature Research: Control-Plane Capabilities

**Domain:** Event routing, dedup, cancellation, promotion gating
**Researched:** 2026-02-17
**Confidence:** HIGH

## Target Outputs (User-Specified)

1. Canonical event model
2. Dedup strategy
3. Cancellation model
4. Promotion gate design
5. Failure/retry semantics

---

## 1. Canonical Event Model

### Table Stakes

| Capability | Why Expected | Complexity |
|------------|--------------|------------|
| Normalize GitHub events → internal events | Single decision point; avoids scattered `if event_type ==` branches | MEDIUM |
| Map issues.labeled/opened → planner.enqueue / builder.enqueue | Clear trigger semantics | LOW |
| Map pull_request opened/synchronize/reopened → reviewer/verifier/security enqueue | PR agents share same trigger | LOW |
| Map workflow_run → governor.evaluate / governor.observe_deploy | Deploy pipeline clarity | LOW |
| Single `should_run(agent, repo, context)` | Config+env precedence; one place to reason | MEDIUM |

### Internal Event Types (Recommended)

```
GitHub Event              → Internal Event(s)
────────────────────────────────────────────────────────────
issues.labeled            → planner.enqueue | builder.enqueue (when agent label)
issues.opened             → planner.enqueue (when agent label on create)
pull_request (opened/     → reviewer.enqueue, verifier.enqueue, security.enqueue
  synchronize/reopened)
workflow_run (verify-main) → governor.evaluate
workflow_run (deploy)     → governor.observe_deploy
check_run (booty/verifier) → memory.surface (current; separate branch)
```

---

## 2. Dedup Strategy

### Standardized Dedup Keys

| Agent Type | Dedup Key | Rationale |
|------------|-----------|------------|
| **PR agents** (Verifier, Reviewer, Security) | `(repo_full_name, pr_number, head_sha)` | Same PR+commit = same work; repo required for multi-tenant |
| **Issue agents** (Planner, Builder) | `(repo, issue_number, plan_hash)` or `(repo, issue_number)` for Builder | Plan-driven Builder uses plan_hash; legacy Builder uses issue |
| **Delivery-based** (Governor deploy trigger) | `delivery_id` or `(repo, head_sha, workflow)` | One trigger per delivery |

### Current Booty Gaps

- **VerifierQueue:** `(pr_number, head_sha)` — missing repo; multi-repo collision risk
- **SecurityQueue:** Same — missing repo
- **ReviewerQueue:** `(repo_full_name, pr_number, head_sha)` ✓ correct
- **Planner:** `delivery_id` — correct for issue events
- **Builder/JobQueue:** `delivery_id` — correct for issue events

### Recommendation

Standardize all PR agents to `(repo_full_name, pr_number, head_sha)`. Add repo to Verifier and Security dedup keys.

---

## 3. Cancellation Model

### Cooperative Cancel (Recommended)

| Aspect | Design |
|--------|--------|
| **Trigger** | New `head_sha` for same PR supersedes old run |
| **Mechanism** | `asyncio.Event` or `cancel_event`; worker checks at phase boundaries |
| **Behavior** | Best-effort — worker exits early; no process kill |
| **Check conclusion** | `conclusion="cancelled"` per GitHub Checks API |
| **Apply to** | Reviewer ✓ (exists); Verifier, Security (add) |

### Anti-Pattern: Hard Cancel

Killing worker process mid-run risks partial state (e.g., check left in_progress). Cooperative cancel allows clean exit and `conclusion=cancelled` update.

### Phase Boundaries for Cancel Check

- Before LLM call (Reviewer)
- Before posting comment
- Before finalizing check run

---

## 4. Promotion Gate Design

### Correct Logic

```
Promotion allowed when:
  1. Verifier check = success (tests passed)
  2. AND (Reviewer disabled OR booty/reviewer conclusion = success OR Reviewer fail-open)
  3. AND (Architect disabled OR agent PR has Architect-approved plan — for plan-originated PRs)
```

### "Second Finisher" Semantics

- **Single promoter:** Verifier only calls `promote_to_ready_for_review`
- **Race:** Verifier and Reviewer run in parallel. When Verifier completes:
  - If Reviewer not done → don't promote; PR stays draft
  - If Reviewer done and success → promote
- **Double-promotion risk:** Verifier runs once per (repo, pr, head_sha). Dedup ensures single run. No double promote from same commit.
- **Stall risk:** If Verifier completes first and Reviewer never runs — bug. Ensure both enqueued from same pull_request event.

### Transactional Check (Optional Hardening)

Before `promote_to_ready_for_review`, re-fetch PR `draft` state. If already `draft=false`, skip (idempotent). GitHub API is idempotent for promote (no-op if already promoted), but explicit check reduces redundant calls.

---

## 5. Failure/Retry Semantics

### Webhook Response

| Scenario | Response | Processing |
|----------|----------|------------|
| Accept and enqueue | 202 Accepted | Async worker processes |
| Duplicate (dedup hit) | 200 `already_processed` | No enqueue |
| Invalid / filtered | 200 `ignored` | No enqueue |

### Worker Failure

- Worker crash: Job may be lost (in-memory queue). Acceptable for Booty scale.
- Promotion API failure: Log, don't retry (user can manually promote)

### GitHub Retry

GitHub does NOT retry on 4xx/5xx. Manual redelivery uses same `X-GitHub-Delivery`. Dedup by delivery_id prevents replay.

---

## Sources

- Booty codebase: webhooks.py, verifier/queue.py, reviewer/queue.py
- Phase 38/40 planning docs
- GitHub Checks API docs

---
*Feature research for: v1.10 Pipeline Correctness*
*Researched: 2026-02-17*
