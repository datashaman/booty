# Phase 45: Promotion Gate Hardening - Research

**Researched:** 2026-02-17
**Domain:** Promotion gating, Architect approval, plan-originated PR detection, idempotent promotion
**Confidence:** HIGH

## Summary

Phase 45 hardens promotion gating: (1) Add Architect approval gate for plan-originated PRs when Architect enabled; (2) Make promote_to_ready_for_review idempotent; (3) Ensure deterministic second-finisher behavior; (4) Verify only Verifier calls promote. CONTEXT.md has locked decisions — plan-originated detection (PR→issue→plan comment), Architect approval from plan comment + disk fallback, idempotency via re-fetch PR draft state.

No new dependencies. Use existing PyGithub, get_plan_comment_body, load_architect_plan_for_issue, get_reviewer_config, get_architect_config. PROMO-01 (Reviewer gate) already implemented in Phase 40; we add Architect gate and idempotency.

**Primary recommendation:** Extend Verifier runner with Architect gate (plan-originated check → Architect approval from plan comment/disk); add idempotency inside promote_to_ready_for_review (re-fetch pr.draft, skip if not draft).

## Standard Stack

| Component | Purpose |
|-----------|---------|
| PyGithub PullRequest.draft | Check if PR is draft before promote (idempotency) |
| PyGithub PullRequest.mark_ready_for_review | Promote draft→ready |
| get_plan_comment_body | Fetch plan comment body for <!-- booty-plan --> detection |
| load_architect_plan_for_issue | Disk fallback for Architect approval |
| get_reviewer_config, get_architect_config | Gate enablement from config |
| reviewer_check_success | Reviewer gate (Phase 40) |

## Architecture Patterns

### Plan-originated PR Detection

**Definition (CONTEXT):** PR has an issue link AND that issue has a `<!-- booty-plan -->` marker.

**Implementation:**
- VerifierJob.issue_number: Router populates from branch `agent/issue-(\d+)`. For agent PRs from Builder, branch is `agent/issue-{N}` where N is the linked issue.
- If job.issue_number is None: treat as not plan-originated (skip Architect gate).
- If job.issue_number set: call `get_plan_comment_body(github_token, repo_url, issue_number)`. If returns None or body lacks `<!-- booty-plan -->`: not plan-originated.
- If body contains `<!-- booty-plan -->`: plan-originated. Check Architect gate when Architect enabled.

**Fallback (CONTEXT):** If plan comment edited/removed, fall back to Architect artifact on disk: `load_architect_plan_for_issue(owner, repo, issue_number, state_dir)` — if returns non-None, treat as plan-originated with Architect approval (disk is advisory; GitHub plan comment is source of truth for approval status).

### Architect Approval Extraction

**Sources (CONTEXT):** Plan comment (<!-- booty-architect -->) and Architect artifact on disk. GitHub wins; disk is advisory.

**Plan comment block format (from architect/output.py):**
```
<!-- booty-architect -->
✓ Approved — Risk: LOW
...notes...
<!-- /booty-architect -->
```

**Approval =** block exists and contains "✓ Approved". Blocked = contains "Architect review required" or "✎ Rewritten" without approved state.

**Extraction:** Reuse regex from comments.py: `r"<!-- booty-architect -->.*?<!-- /booty-architect -->"` (re.DOTALL). Check if matched content includes "✓ Approved".

**Disk fallback:** `load_architect_plan_for_issue` returns ArchitectPlan or None. If returns non-None: advisory approval (artifact exists = Architect ran and approved). But source of truth is GitHub; use disk only when plan comment unavailable or indeterminate.

### Idempotency (PROMO-05)

**Strategy (CONTEXT):** Re-fetch PR draft state before promote; if not draft (already ready), skip.

**Implementation in promote_to_ready_for_review:**
1. repo = _get_repo(...); pr = repo.get_pull(pr_number)
2. if not pr.draft: log "pr_already_ready", pr_number=pr_number; return (no-op)
3. pr.mark_ready_for_review()
4. log "pr_promoted", pr_number=pr_number

**PR missing/inaccessible:** PyGithub raises GithubException. Caller (Verifier) catches and logs. Per CONTEXT: treat as no-op, log and return (no raise/retry) — actually the function currently raises; CONTEXT says "no raise/retry" for missing PR. Clarify: idempotency handles already-ready; missing PR is exceptional (caller handles). Keep existing retry/raise for 5xx/network.

### Gate Check Order (CONTEXT)

1. Reviewer first: can_promote = reviewer_check_success OR !reviewer_enabled
2. Architect second: if plan-originated and architect_enabled, can_promote = architect_approved AND can_promote

**Logging:** promotion_waiting_reviewer (existing), promotion_waiting_architect (new).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Fetch plan comment | Custom issue comment iteration | get_plan_comment_body |
| Parse Architect approval | Custom comment scraper | Regex on <!-- booty-architect --> block |
| Load Architect artifact | Custom file reader | load_architect_plan_for_issue |
| Check PR draft | Custom API call | pr.draft (PyGithub) |

## Common Pitfalls

### Pitfall: Race with Architect

**What:** Verifier may complete before Architect updates plan comment.
**Why:** Architect runs async; plan comment update may lag.
**How to avoid:** At promote-time, check both sources (plan comment first, disk fallback). If neither shows approval, log promotion_waiting_architect and do not promote. Deterministic: Verifier checks at promote-time; no race.

### Pitfall: plan-originated False Negatives

**What:** Branch may not follow agent/issue-N pattern; issue_number could be None.
**Why:** CONTEXT: "If we cannot determine plan-originated (e.g. missing issue link), treat as not plan-originated and skip Architect gate."
**How to avoid:** When issue_number is None, skip Architect gate. Log for metrics if desired. No fail-closed.

### Pitfall: Double Promote

**What:** Verifier and Reviewer might both try to promote (second-finisher).
**Why:** PROMO-03: Only Verifier calls promote. PROMO-05: Idempotent. If Reviewer ever called promote (it shouldn't), idempotency would make second call no-op.
**How to avoid:** grep-verify only Verifier has promote_to_ready_for_review. Idempotency as belt-and-suspenders.

## Code Examples

### Architect Approval from Plan Comment

```python
def architect_approved_from_plan_comment(body: str | None) -> bool:
    """True if <!-- booty-architect --> block contains ✓ Approved."""
    if not body:
        return False
    match = re.search(
        r"<!-- booty-architect -->.*?<!-- /booty-architect -->",
        body,
        re.DOTALL,
    )
    return match is not None and "✓ Approved" in (match.group(0) or "")
```

### Idempotent Promote (inside promotion.py)

```python
def promote_to_ready_for_review(...) -> None:
    repo = _get_repo(github_token, repo_url)
    pr = repo.get_pull(pr_number)
    if not pr.draft:
        logger.info("pr_already_ready", pr_number=pr_number)
        return
    pr.mark_ready_for_review()
    logger.info("pr_promoted", pr_number=pr_number)
```

## PROMO Requirements Mapping

| Req | Implementation |
|-----|----------------|
| PROMO-01 | Already: reviewer_check_success, fail-open, disabled |
| PROMO-02 | New: plan-originated check, Architect approval from comment/disk |
| PROMO-03 | grep-verify: only Verifier imports/calls promote_to_ready_for_review |
| PROMO-04 | Check Reviewer then Architect at promote-time; no caching |
| PROMO-05 | Re-fetch pr.draft; skip if not draft |

## Sources

### Primary (HIGH confidence)
- src/booty/verifier/runner.py — current promotion flow
- src/booty/github/promotion.py — promote_to_ready_for_review
- src/booty/github/comments.py — get_plan_comment_body, architect block regex
- src/booty/architect/output.py — <!-- booty-architect --> format
- src/booty/architect/artifact.py — load_architect_plan_for_issue
- 45-CONTEXT.md — locked decisions

### Secondary
- 40-RESEARCH.md — Reviewer gate pattern
- PyGithub PullRequest.draft — GitHub REST API schema

---

*Phase: 45-promotion-gate-hardening*
*Research date: 2026-02-17*
