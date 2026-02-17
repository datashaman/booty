# Architecture Research: Event Router and Control Plane

**Domain:** Multi-agent pipeline event routing, Planner→Architect→Builder flow
**Researched:** 2026-02-17
**Confidence:** HIGH

## Canonical Event Model

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     GitHub Webhooks (POST /webhooks/github)               │
├─────────────────────────────────────────────────────────────────────────┤
│  X-GitHub-Event, X-GitHub-Delivery, payload                              │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SINGLE EVENT ROUTER (should_run)                       │
├─────────────────────────────────────────────────────────────────────────┤
│  Normalize: issues.labeled → planner | builder                           │
│             pull_request → reviewer | verifier | security                │
│             workflow_run → governor.evaluate | governor.observe            │
│  Decision:  should_run(agent, repo, context) with config+env precedence  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Issue Agents  │     │ PR Agents       │     │ Workflow Agents  │
│ Planner       │     │ Reviewer        │     │ Governor         │
│ Architect     │     │ Verifier        │     │                  │
│ Builder       │     │ Security        │     │                  │
└───────────────┘     └─────────────────┘     └─────────────────┘
```

### Planner→Architect→Builder Correctness

**Current flow (webhooks.py + main.py):**
- `issues.labeled` with agent label → check plan/architect
- If Architect-approved plan exists → enqueue Builder directly
- Else if plan exists but unreviewed → enqueue Architect (or Planner if no plan)
- Builder consumes `get_plan_for_builder` → Architect artifact first, Planner plan fallback

**Recommended routing logic:**

```
On issues.labeled (agent label):
  plan, unreviewed = get_plan_for_builder(owner, repo, issue_number)
  if architect_enabled:
    if plan and not unreviewed:  → builder.enqueue
    elif plan and unreviewed:    → architect.enqueue
    else:                        → planner.enqueue
  else:
    if plan:                     → builder.enqueue
    else:                        → planner.enqueue
```

**Builder consumption:** Architect artifact first. Fallback to Planner plan only when explicitly enabled (compat flag for repos without Architect).

---

## Integration Points

### Existing Components → Changes

| Component | Current | Change |
|-----------|---------|--------|
| webhooks.py | 800+ lines, many branches | Extract router; normalize events |
| VerifierQueue | (pr_number, head_sha) | Add repo to dedup key |
| SecurityQueue | (pr_number, head_sha) | Add repo to dedup key |
| ReviewerQueue | (repo, pr_number, head_sha) ✓ | No change |
| Verifier runner | No cancel | Add cooperative cancel (mirror Reviewer) |
| Security runner | No cancel | Add cooperative cancel (optional; Security is fast) |

### Data Flow: promotion gate

```
Verifier completes
    → tests_passed?
    → reviewer_enabled? → reviewer_check_success(repo, head_sha)?
    → architect_enabled? → (for plan PRs) Architect approved?
    → promote_to_ready_for_review
```

---

## Build Order (for Roadmap)

1. **Event router extraction** — Single should_run; normalize events
2. **Dedup alignment** — Add repo to Verifier/Security; document standard keys
3. **Planner→Architect→Builder wiring audit** — Verify logic; add compat flag
4. **Promotion gate hardening** — Architect check for plan PRs; idempotent promote
5. **Cancel semantics** — Extend to Verifier (Security optional)
6. **Operator visibility** — Structured skip logs; booty status

---

## Anti-Patterns

### Scattered routing
**What:** Each event type handled in isolation with duplicate config checks.
**Do:** Single router with `should_run(agent, repo, context)`.

### Dedup key without repo
**What:** `(pr_number, head_sha)` — PR# can collide across repos.
**Do:** `(repo_full_name, pr_number, head_sha)`.

### Both Verifier and Reviewer promote
**What:** Race; double promote; nondeterministic.
**Do:** Verifier only promotes; gates on Reviewer success when enabled.

---
*Architecture research for: v1.10 Pipeline Correctness*
*Researched: 2026-02-17*
