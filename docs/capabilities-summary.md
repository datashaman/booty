# Booty Capabilities Summary (v1.7)

Booty is a self-managing software builder powered by AI. GitHub is the interface — issues in, PRs out. No custom UI.

---

## Builder Agent (v1.0, v1.1)

**Planner-first:** Pure executor — only runs when a valid Plan artifact exists. Plan ready → Builder runs automatically (autonomous). Trigger: `agent` label. Uses plan's goal, steps, handoff_to_builder for execution. No fallback to raw issue interpretation.

## Verifier Agent (v1.2)

Runs on every PR, enforces gates for agent PRs: runs tests in clean env, validates `.booty.yml`, enforces diff limits, detects hallucinated imports / compile failures. Blocks merge and promotion when checks fail. Publishes the `booty/verifier` GitHub check.

## Deploy & Observability (v1.3)

Automated deployment via GitHub Actions (SSH to DigitalOcean, deploy.sh, health check). Sentry APM for error tracking and release correlation. Observability agent ingests Sentry alerts via webhook, filters (severity, dedup, cooldown), creates GitHub issues with `agent` for follow-up.

## Release Governor (v1.4)

Gates production deployment. When Verify main workflow completes, computes risk from paths touched (LOW/MEDIUM/HIGH), applies approval rules, and either triggers deploy via `workflow_dispatch` or posts HOLD with reason and unblock instructions. Commit status `booty/release-governor`, CLI: `booty governor status | simulate | trigger`.

## Security Agent (v1.5)

Runs on every PR, publishes required check `booty/security`. Secret scanning (gitleaks/trufflehog), dependency audit (pip/npm/composer/cargo), permission drift on sensitive paths → ESCALATE to Governor. Blocks merge on high-severity findings.

## Memory Agent (v1.6)

Append-only `memory.jsonl` store. Ingests from Observability, Governor, Security, Verifier, Revert with dedup. Surfaces related history in PR comments, Governor HOLD, Observability incidents. CLI: `booty memory status | query`. Informational only.

## Planner Agent (v1.7)

**Single work originator.** Turns GitHub issues, Observability incidents, or operator CLI prompts (`booty plan --text`) into structured Plan JSON: goal, steps (max 12), risk_level, touch_paths, handoff_to_builder. Triggers on `agent` label (opened or labeled). System figures out Planner→Builder. Outputs plan as issue comment + artifact. Idempotent within 24h. Plan ready → Builder runs autonomously.

---

## End-to-end flow (Planner-first, autonomous)

1. Issue/incident → add `agent` → Planner runs → Plan stored
2. Plan ready → Builder runs automatically (no extra label)
2. Verifier runs checks on PR
3. Merge → Verify main runs on main
4. Governor decides deploy → HOLD or triggers Deploy workflow
5. Sentry monitors production
6. Observability creates issues for incidents → Planner picks up → Builder runs when plan ready
7. Security and Memory support each stage
