# Booty Capabilities Summary (v1.10)

Booty is a self-managing software builder powered by AI. GitHub is the interface — issues in, PRs out. No custom UI.

---

## Dedup Keys

Standard keys for deduplication across agents. Same key = same work; avoids duplicate runs.

**PR agents (Verifier, Reviewer, Security):**

| Key | Serialization | Purpose |
|-----|---------------|---------|
| `(repo_full_name, pr_number, head_sha)` | `{repo_full_name}:{pr_number}:{head_sha}` | Same PR+commit = same work; repo required for multi-tenant correctness |

**Issue agents:**

| Agent | Key | Notes |
|-------|-----|-------|
| Planner | `(repo, delivery_id)` | delivery_id is GitHub X-GitHub-Delivery; globally unique per webhook |
| Builder (issue-driven) | `(repo, delivery_id)` | Same as Planner for issue-triggered jobs |
| Builder (plan-driven) | `(repo, plan_hash)` | Phase 44 — reserve |
| Architect | TBD | Phase 44 — reserve slot |

---

## Builder Agent (v1.0, v1.1)

**Planner-first:** Pure executor — only runs when a valid Plan artifact exists. Plan ready → Architect (when enabled) → Builder runs automatically (autonomous). Trigger: `agent` label. Uses plan's goal, steps, handoff_to_builder for execution. No fallback to raw issue interpretation.

## Architect Agent (v1.8)

**Plan validation.** Sits between Planner and Builder. Validates structural integrity, path consistency, risk accuracy; detects ambiguity and overreach. Rewrites plans when needed. When enabled (per `.booty.yml`), Builder runs only after Architect approval. Persists approved plan to `~/.booty/state/plans/<repo>/<issue>-architect.json`. CLI: `booty architect status`, `booty architect review --issue N`.

## Reviewer Agent (v1.9)

**Code quality review.** Sits between Builder and Verifier. AI-driven review of PR diffs for engineering quality: maintainability, overengineering, duplication, test quality, naming, architectural drift. Publishes `booty/reviewer` check. APPROVED / APPROVED_WITH_SUGGESTIONS / BLOCKED. Builder promotion requires reviewer success for agent PRs. Fail-open on infra/LLM failure. When enabled (per `.booty.yml` reviewer block); disabled by default. CLI: `booty reviewer status`. Persisted metrics: reviews_total, reviews_blocked, reviews_suggestions, reviewer_fail_open.

## Verifier Agent (v1.2)

Runs on every PR, enforces gates for agent PRs: runs tests in clean env, validates `.booty.yml`, enforces diff limits, detects hallucinated imports / compile failures. Blocks merge and promotion when checks fail. Publishes the `booty/verifier` GitHub check. When tests pass but Reviewer has not yet succeeded, Verifier logs promotion_waiting_reviewer (OPS-04).

## Deploy & Observability (v1.3)

Automated deployment via GitHub Actions (SSH to DigitalOcean, deploy.sh, health check). Sentry APM for error tracking and release correlation. Observability agent ingests Sentry alerts via webhook, filters (severity, dedup, cooldown), creates GitHub issues with `agent` for follow-up.

## Release Governor (v1.4)

Gates production deployment. On push to main, Booty runs verification (tests); on success, computes risk from paths touched (LOW/MEDIUM/HIGH), applies approval rules, and either triggers deploy via `workflow_dispatch` or posts HOLD with reason and unblock instructions. Commit status `booty/release-governor`, CLI: `booty governor status | simulate | trigger`.

## Security Agent (v1.5)

Runs on every PR, publishes required check `booty/security`. Secret scanning (gitleaks/trufflehog), dependency audit (pip/npm/composer/cargo), permission drift on sensitive paths → ESCALATE to Governor. Blocks merge on high-severity findings.

## Memory Agent (v1.6)

Append-only `memory.jsonl` store. Ingests from Observability, Governor, Security, Verifier, Revert with dedup. Surfaces related history in PR comments, Governor HOLD, Observability incidents. CLI: `booty memory status | query`. Informational only.

## Planner Agent (v1.7)

**Single work originator.** Turns GitHub issues, Observability incidents, or operator CLI prompts (`booty plan --text`) into structured Plan JSON: goal, steps (max 12), risk_level, touch_paths, handoff_to_builder. Triggers on `agent` label (opened or labeled). System figures out Planner→Architect→Builder. Outputs plan as issue comment + artifact. Idempotent within 24h. Plan ready → Architect (when enabled) → Builder runs autonomously.

---

## End-to-end flow (Planner-first, autonomous)

1. Issue/incident → add `agent` → Planner runs → Plan stored
2. Architect validates/rewrites plan (when enabled in .booty.yml)
3. Plan approved → Builder runs automatically (no extra label)
4. Builder opens PR → Reviewer runs (when enabled) → Verifier runs checks on PR
5. Merge → Booty verifies main (runs tests); on success, Governor decides deploy → HOLD or triggers Deploy workflow
7. Sentry monitors production
8. Observability creates issues for incidents → Planner picks up → Architect → Builder runs when plan ready
9. Security and Memory support each stage
