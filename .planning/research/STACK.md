# Stack Research

**Domain:** Observability — deploy automation, APM, alert-to-issue pipeline
**Researched:** 2026-02-15
**Confidence:** HIGH

## Recommended Stack

### Core Technologies (New for v1.3)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| sentry-sdk | 2.x (Python) | Error tracking, release correlation, APM | Official Sentry Python SDK; FastAPI integration built-in; `release` param maps to git SHA; structlog compatible |
| GitHub Actions | — | Deploy workflow (SSH to DO) | Booty is already on GitHub; workflow triggers on push/merge; no new infra |
| SSH (appleboy/ssh-action or native) | latest | Remote command execution | deploy.sh already exists; workflow invokes same pattern |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sentry-sdk[fastapi] | same as core | FastAPI + Starlette integrations | Bootstrap Sentry in main app |
| — | — | Webhook HMAC verification | Observability agent; use stdlib `hmac` + `hashlib` |
| — | — | PyGithub | Already present; Observability agent creates issues |

### Integration with Existing Stack

| Existing | New Addition | Integration Point |
|----------|--------------|-------------------|
| FastAPI | sentry_sdk.init() at app startup | Before app creation; set `release`, `environment` |
| structlog | Sentry breadcrumbs | Sentry can attach log context; optional |
| deploy.sh | .github/workflows/deploy.yml | Workflow calls `./deploy.sh` or equivalent SSH |
| PyGithub | Issue creation | Same pattern as Builder; Observability agent uses it |

## Installation

```bash
# Sentry Python SDK
pip install sentry-sdk[fastapi]
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Sentry | Datadog, New Relic | If org already has APM contract |
| GitHub Actions deploy | Manual deploy.sh | Keeps current flow; CI/CD is explicit add |
| Sentry webhook | Sentry email/Slack → custom parser | Webhook is direct, no parsing needed |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Custom APM from scratch | High complexity, Sentry is mature | sentry-sdk |
| Polling Sentry API for alerts | Latency, rate limits | Webhook (push) |
| Storing webhook secret in code | Security risk | Pydantic Settings from env |

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| sentry-sdk | Python 3.10+ | Booty uses 3.11+ |
| FastAPI integration | Starlette 0.14+ | Already in Booty deps |

## Sources

- /getsentry/sentry-python (Context7) — FastAPI init, release, integrations
- /getsentry/sentry-docs (Context7) — Webhook signature verification, payload
- /websites/github_en_actions — Secrets, shell, SSH patterns
- deploy.sh — Existing deploy flow

---
*Stack research for: v1.3 Observability*
*Researched: 2026-02-15*
