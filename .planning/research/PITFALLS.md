# Pitfalls Research: Control-Plane and Event Routing

**Domain:** Event routing, dedup, promotion, cancellation
**Researched:** 2026-02-17
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Dedup Key Collision Across Repos

**What goes wrong:** Verifier and Security use `(pr_number, head_sha)` without repo. In multi-tenant deployment, PR #42 in repo A and PR #42 in repo B could share same head_sha (unlikely but possible) or hash collision; dedup incorrectly skips work.

**Why it happens:** Verifier was built single-repo first; repo added to config later. Reviewer correctly added repo from day one.

**How to avoid:** Standardize all PR agents to `(repo_full_name, pr_number, head_sha)`.

**Warning signs:** "Verifier didn't run for my PR" when another repo's PR was processed first.

**Phase to address:** Dedup alignment phase.

---

### Pitfall 2: Promotion Race — Double Promote

**What goes wrong:** If both Verifier and Reviewer called `promote_to_ready_for_review`, duplicate API calls; or worse, logic bug causes both to think they "won" and promote.

**Why it happens:** "Second finisher promotes" sounds like either could promote. Without single-owner design, both might try.

**How to avoid:** **Verifier only** promotes. Reviewer never promotes. Verifier gates on `reviewer_check_success` when Reviewer enabled. Single promote point.

**Warning signs:** Two promote API calls for same PR; or PR promoted then "demoted" by conflicting logic.

**Phase to address:** Promotion gate correctness phase.

---

### Pitfall 3: Promotion Stall — Verifier Finishes First, Reviewer Never Runs

**What goes wrong:** Verifier completes, checks Reviewer — not done. Doesn't promote. Reviewer never runs (bug, crash, filtered). PR stuck in draft forever.

**Why it happens:** Reviewer enqueue failed or was skipped; or Reviewer and Verifier use different agent-PR detection and Reviewer didn't get the job.

**How to avoid:** Ensure both Reviewer and Verifier enqueued from same `pull_request` event with same agent-PR gate. Log when Verifier skips promote (promotion_waiting_reviewer). Operator visibility: "why nothing happened."

**Warning signs:** PR green on both checks but still draft; logs show promotion_waiting_reviewer repeatedly.

**Phase to address:** Promotion gate + operator visibility.

---

### Pitfall 4: Hard Cancel of LLM Worker

**What goes wrong:** Kill Verifier/Reviewer worker mid-run. Check left in `in_progress`; GitHub shows stale status. Or partial comment posted.

**Why it happens:** Implementer uses `task.cancel()` or process kill instead of cooperative cancel.

**How to avoid:** Cooperative cancel: worker checks `cancel_event.is_set()` at phase boundaries; exits with `conclusion=cancelled`. No hard kill.

**Warning signs:** Checks stuck "in progress"; logs show worker killed.

**Phase to address:** Cancel semantics phase.

---

### Pitfall 5: Silent Skip — No Log When Event Ignored

**What goes wrong:** Webhook receives event; routing logic skips (disabled, not agent PR, dedup hit). No structured log. Operator cannot debug "why didn't Booty run?"

**Why it happens:** Early return `{"status":"ignored"}` without logging decision and reason.

**How to avoid:** Emit structured log: `agent, repo, event_type, decision=skip, reason`. Example: `reason=disabled`, `reason=not_agent_pr`, `reason=dedup_hit`.

**Warning signs:** User reports "Booty didn't run" and logs show nothing.

**Phase to address:** Operator visibility phase.

---

### Pitfall 6: Architect Gate Missing in Promotion

**What goes wrong:** Agent PR from plan; Architect disabled in config. Builder ran from Planner plan. Verifier promotes when tests+reviewer pass. Correct. But: Architect enabled, plan exists, Architect blocked — Builder shouldn't have run. If Builder did run (bug), Verifier could promote without Architect approval.

**Why it happens:** Promotion gate only checks Verifier + Reviewer. Architect approval is a Builder enqueue gate, not a promote gate. For plan-originated PRs, Builder only runs after Architect. So PR existence implies Architect approved. But if wiring is wrong, could promote without Architect.

**How to avoid:** Promotion gate: for agent PRs that have plan (linked issue with plan), ensure Architect approved. Re-fetch plan status if needed. Belt-and-suspenders.

**Warning signs:** PR promoted with Architect having blocked the plan (shouldn't happen if wiring correct).

**Phase to address:** Promotion gate correctness phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| In-memory dedup (no persistence) | Simple; no DB | Process restart loses history; replay can duplicate | OK for Booty scale; document |
| Security without cancel | Faster to ship | New push leaves old Security run in flight | Acceptable; Security is fast |
| No booty status CLI | Less work | Operator blind to queue depth, last run | Not acceptable for v1.10 |

---

## "Looks Done But Isn't" Checklist

- [ ] **Event router:** Single should_run — verify no duplicate config checks in legacy branches
- [ ] **Dedup:** All PR agents use (repo, pr_number, head_sha) — grep for is_duplicate calls
- [ ] **Promotion:** Only Verifier calls promote — grep for promote_to_ready_for_review
- [ ] **Cancel:** Verifier checks cancel_event at phase boundaries — grep runner for cancel
- [ ] **Skip logging:** Every early return logs agent, reason — audit webhooks.py returns

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Dedup collision | LOW | Add repo to keys; redeploy; replay may duplicate (one-time) |
| Double promote | LOW | No user impact; promote is idempotent |
| Promotion stall | MEDIUM | Manual promote; fix enqueue gate; add visibility |
| Hard cancel | MEDIUM | Implement cooperative cancel; restart workers |
| Silent skip | LOW | Add logging; redeploy |

---
*Pitfalls research for: v1.10 Pipeline Correctness*
*Researched: 2026-02-17*
