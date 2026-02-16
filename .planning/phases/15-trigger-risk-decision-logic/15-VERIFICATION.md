---
phase: 15-trigger-risk-decision-logic
status: passed
verified_at: 2026-02-16
---

# Phase 15: Trigger, Risk & Decision Logic — Verification

## Goal

workflow_run handler, risk scoring from paths, decision rules, cooldown/rate limit.

## Must-Haves Verified

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Governor receives workflow_run (verification workflow on main, conclusion=success) | ✓ | webhooks.py workflow_run branch, filters action=completed, conclusion=success, head_branch=main |
| Uses head_sha from payload (never latest main) | ✓ | handler.py: head_sha = wr.get("head_sha"); comparison = gh_repo.compare(production_sha, head_sha) |
| Risk scoring: HIGH (workflows, infra, lockfiles, migrations), MEDIUM (manifests), LOW (rest) | ✓ | risk.py PathSpec from high_risk_paths, medium_risk_paths; config defaults |
| Hard holds: deploy not configured; first deploy without approval; degraded + high-risk | ✓ | decision.py: deploy_not_configured, first_deploy_required, degraded_high_risk |
| Approval: LOW auto-ALLOW; MEDIUM hold if incident; HIGH hold unless approval | ✓ | decision.py: allow_low, allow_medium/degraded_medium_hold, allow_high_approved/high_risk_no_approval |
| Cooldown and max_deploys_per_hour enforced | ✓ | decision.py cooldown/rate_limit; store.append_deploy_to_history, get_deploys_in_last_hour |

## Artifacts Verified

- `src/booty/release_governor/risk.py` — compute_risk_class ✓
- `src/booty/release_governor/decision.py` — compute_decision ✓
- `src/booty/release_governor/handler.py` — handle_workflow_run ✓
- `src/booty/webhooks.py` — workflow_run branch ✓
- `tests/test_release_governor_risk.py` — 6 tests ✓
- `tests/test_release_governor_decision.py` — 10 tests ✓
- `tests/test_release_governor_handler.py` — 2 tests ✓

## Human Verification

None required.

## Gaps

None.
