# Project Research Summary

**Project:** Booty
**Domain:** Pipeline correctness — event routing, dedup, promotion, cancellation
**Researched:** 2026-02-17
**Confidence:** HIGH

## Executive Summary

v1.10 focuses on the control plane: ensuring the right agents run at the right time, exactly once, with correct promotion and no silent stalls. Research validates that GitHub webhooks do not auto-retry failed deliveries, that X-GitHub-Delivery is stable on redelivery (enabling dedup), and that cooperative cancellation is the right model for long-running LLM tasks. The primary risks are: (1) inconsistent dedup keys (Verifier/Security lack repo), (2) promotion race if more than one component promotes, (3) silent skips with no operator visibility. A single canonical event router with standardized dedup and explicit skip logging addresses these. Requirements can be derived directly from the five target outputs: canonical event model, dedup strategy, cancellation model, promotion gate design, failure/retry semantics.

## Key Findings

### Canonical Event Model

- Normalize GitHub events to internal events: issues.labeled/opened → planner|builder; pull_request → reviewer|verifier|security; workflow_run → governor.
- Single `should_run(agent, repo, context)` with config+env precedence.
- Planner→Architect→Builder: route by plan/architect artifact; Builder consumes Architect first.

### Dedup Strategy

- **PR agents:** `(repo_full_name, pr_number, head_sha)` — all three. Verifier and Security currently omit repo; fix.
- **Issue agents:** `(repo, issue_number, plan_hash)` or delivery_id for delivery-scoped.
- Standardize; document.

### Cancellation Model

- Cooperative cancel: `asyncio.Event`, worker checks at phase boundaries, `conclusion=cancelled` on exit.
- New head_sha supersedes; request_cancel for prior run. Reviewer has it; extend to Verifier (Security optional).

### Promotion Gate Design

- Single promoter: Verifier only.
- Gate: verifier success AND (reviewer disabled OR reviewer success OR fail-open) AND (architect approved for plan PRs when enabled).
- Idempotent promote (optional re-fetch draft state).

### Failure/Retry Semantics

- 202 on accept; 200 already_processed on dedup; 200 ignored on filter.
- Structured skip log: agent, repo, event_type, decision=skip, reason.
- GitHub does not auto-retry; manual redelivery same delivery_id.

## Implications for Roadmap

### Phase Order (suggested)

1. **Event Router** — Extract single router; normalize events; should_run decision point.
2. **Dedup Alignment** — Add repo to Verifier/Security dedup keys; document standard.
3. **Planner→Architect→Builder Wiring** — Audit and fix routing; Builder compat flag.
4. **Promotion Gate Hardening** — Architect check for plan PRs; idempotent promote.
5. **Cancel Semantics** — Extend cooperative cancel to Verifier.
6. **Operator Visibility** — Structured skip logs; booty status CLI.

### Research Flags

- **Phase 2 (Dedup):** VerifierQueue and SecurityQueue signatures change; callers must pass repo.
- **Phase 4 (Promotion):** Architect gate — verify when plan-originated PRs require Architect approval at promote time.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Event model | HIGH | Clear mapping; Booty codebase reviewed |
| Dedup | HIGH | Reviewer correct; Verifier/Security gap documented |
| Cancel | HIGH | Reviewer pattern exists; extend |
| Promotion | HIGH | Phase 40 research + current impl |
| Retry/skip | HIGH | GitHub docs + best practices |

**Overall confidence:** HIGH

### Gaps to Address

- Architect approval at promote time: Builder enqueue gate may be sufficient; add promote-time check as hardening.

---
*Research completed: 2026-02-17*
*Ready for roadmap: yes*
