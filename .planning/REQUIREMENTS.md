# Requirements: Booty v1.10 Pipeline Correctness

**Defined:** 2026-02-17
**Core Value:** A Builder agent that can take a GitHub issue and produce a working PR with tested code — the foundation everything else builds on.

**Milestone goal:** Given any relevant GitHub event, Booty runs exactly the right agents exactly once, promotes correctly, and never stalls silently.

## v1.10 Requirements

### Event Router (ROUTE)

- [x] **ROUTE-01**: Operator can observe a single canonical event router that normalizes GitHub events into internal events before enqueue
- [x] **ROUTE-02**: issues.labeled/opened with agent label maps to planner.enqueue or builder.enqueue per routing rules
- [x] **ROUTE-03**: pull_request (opened/synchronize/reopened) maps to reviewer.enqueue, verifier.enqueue, security.enqueue per agent config
- [x] **ROUTE-04**: workflow_run (verify-main, deploy) maps to governor.evaluate or governor.observe_deploy
- [x] **ROUTE-05**: Single should_run(agent, repo, context) decision point with config+env precedence governs all enqueue decisions

### Planner→Architect→Builder Wiring (WIRE)

- [x] **WIRE-01**: When agent:builder (or equivalent) arrives and Architect-approved plan exists for that issue+plan_hash, enqueue Builder directly
- [x] **WIRE-02**: When plan exists but not Architect-approved, enqueue Architect (not Builder)
- [x] **WIRE-03**: When no plan exists, enqueue Planner
- [x] **WIRE-04**: Builder consumes Architect artifact first; fallback to Planner plan only when compat flag enabled
- [x] **WIRE-05**: Routing logic is auditable and documented (config precedence, Architect/Planner disabled behavior)

### Promotion Gating (PROMO)

- [x] **PROMO-01**: Promotion happens only when Verifier success AND (Reviewer success OR Reviewer fail-open OR Reviewer disabled)
- [x] **PROMO-02**: For agent PRs that originated from a plan, promotion requires Architect approval when Architect enabled
- [x] **PROMO-03**: Verifier is the only component that calls promote_to_ready_for_review
- [x] **PROMO-04**: "Second finisher promotes" logic is deterministic (Verifier checks all gates at promote-time; no race)
- [x] **PROMO-05**: promote_to_ready_for_review is idempotent (re-fetch draft state or rely on GitHub no-op; no double-promote)

### Dedup and Cancel (DEDUP)

- [x] **DEDUP-01**: PR agents (Verifier, Reviewer, Security) use dedup key (repo_full_name, pr_number, head_sha)
- [x] **DEDUP-02**: Issue agents use documented dedup keys (repo, issue_number, plan_hash or delivery_id as appropriate)
- [x] **DEDUP-03**: New head_sha for same PR supersedes old run — prior run marked cancelled; best-effort cooperative cancel in workers
- [x] **DEDUP-04**: Verifier and Security queues accept repo in dedup; VerifierQueue/SecurityQueue signatures updated
- [x] **DEDUP-05**: Verifier runner checks cancel_event at phase boundaries; exits with conclusion=cancelled when superseded

### Operator Visibility (OPS)

- [ ] **OPS-01**: When an event is ignored (skip), emit structured log with agent, repo, event_type, decision=skip, reason
- [ ] **OPS-02**: Skip reasons include: disabled, not_agent_pr, missing_config, dedup_hit
- [ ] **OPS-03**: booty status CLI shows enabled agents, last run timestamps, queue depth (if available)
- [ ] **OPS-04**: Verifier logs promotion_waiting_reviewer when tests pass but Reviewer not yet success

## Future Requirements

Deferred to later milestones:

- **OPS-05**: Persistent queue metrics (requires queue instrumentation)
- **DEDUP-06**: Security cooperative cancel (optional; Security runs fast)
- **ROUTE-06**: Subscription-based routing (agents register for events)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Distributed lock for promotion | Single-instance sufficient; Verifier-only promote is enough |
| Message queue (SQS/RabbitMQ) for webhooks | In-memory queue sufficient for Booty scale |
| Persistent dedup store | In-memory acceptable; document restart semantics |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ROUTE-01 | 42 | Complete |
| ROUTE-02 | 42 | Complete |
| ROUTE-03 | 42 | Complete |
| ROUTE-04 | 42 | Complete |
| ROUTE-05 | 42 | Complete |
| DEDUP-01 | 43 | Complete |
| DEDUP-02 | 43 | Complete |
| DEDUP-04 | 43 | Complete |
| WIRE-01 | 44 | Complete |
| WIRE-02 | 44 | Complete |
| WIRE-03 | 44 | Complete |
| WIRE-04 | 44 | Complete |
| WIRE-05 | 44 | Complete |
| PROMO-01 | 45 | Complete |
| PROMO-02 | 45 | Complete |
| PROMO-03 | 45 | Complete |
| PROMO-04 | 45 | Complete |
| PROMO-05 | 45 | Complete |
| DEDUP-03 | 46 | Complete |
| DEDUP-05 | 46 | Complete |
| OPS-01 | 47 | Pending |
| OPS-02 | 47 | Pending |
| OPS-03 | 47 | Pending |
| OPS-04 | 47 | Pending |

**Coverage:**

- v1.10 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-17*
*Last updated: 2026-02-17 after research synthesis*
