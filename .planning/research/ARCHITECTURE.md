# Architecture Research

**Domain:** Observability — deploy automation, Sentry APM, alert-to-issue pipeline
**Researched:** 2026-02-15
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GitHub (CI/CD + Issues)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  push to main → Actions workflow → SSH → DO server                          │
│  Observability agent creates issues ← Sentry webhook                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  Builder picks up agent:builder issues (existing flow)                       │
└─────────────────────────────────────────────────────────────────────────────┘
         ↑                    ↑                          ↑
         │                    │                          │
┌────────┴────────┐  ┌───────┴───────┐  ┌───────────────┴───────────────────┐
│ GitHub Actions  │  │  Sentry.io     │  │  Booty (DO server)                 │
│ .github/        │  │  APM + Alerts  │  │  FastAPI + Sentry SDK              │
│ workflows/      │  │  Webhooks →    │  │  Observability agent (webhook)     │
│ deploy.yml      │  │  Booty         │  │  Builder, Verifier (existing)      │
└─────────────────┘  └───────────────┘  └───────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|-----------------|------------------------|
| Deploy workflow | Trigger on main push; SSH to DO; run deploy.sh | .github/workflows/deploy.yml; appleboy/ssh-action or shell with ssh |
| Sentry SDK | Capture errors, set release/env, send to Sentry | sentry_sdk.init() at app startup |
| Observability agent | Receive Sentry webhook; filter; create GitHub issue | FastAPI POST route; HMAC verify; PyGithub create_issue |
| Cooldown store | Prevent duplicate issues per fingerprint | In-memory dict with TTL; or Redis later |

## Recommended Project Structure

```
booty/
├── .github/workflows/
│   └── deploy.yml              # NEW: Trigger on push, SSH deploy
├── src/booty/
│   ├── main.py                 # MODIFY: Add sentry_sdk.init()
│   ├── observability/          # NEW
│   │   ├── __init__.py
│   │   ├── webhook.py          # Sentry webhook handler
│   │   ├── filters.py          # Severity, dedup, cooldown
│   │   └── issue_creator.py    # GitHub issue creation
│   ├── builder/                # (existing)
│   ├── verifier/               # (existing)
│   └── github/                 # (existing)
├── deploy.sh                   # (existing)
└── pyproject.toml              # MODIFY: Add sentry-sdk
```

### Structure Rationale

- **observability/:** Mirrors builder/, verifier/ — agent-per-subsystem pattern.
- **webhook.py:** Single route; verify → filter → create issue.
- **filters.py:** Reusable logic; testable without HTTP.

## Architectural Patterns

### Pattern 1: Webhook → Verify → Filter → Act

**What:** Receive webhook, verify signature, apply filters, then side effect (create issue).
**When to use:** All inbound webhooks (already used for GitHub).
**Trade-offs:** Fail fast on verify; filter before any external call.

### Pattern 2: Release as Git SHA

**What:** `release="booty@$(git rev-parse HEAD)"` or from env at deploy time.
**When to use:** Sentry init; enables Sentry UI to correlate errors with deploy.
**Trade-offs:** Must set at startup; CI passes SHA to deploy.

### Pattern 3: Cooldown Dict

**What:** `{fingerprint: last_created_ts}` with TTL; skip if within cooldown.
**When to use:** Observability agent; simple for MVP.
**Trade-offs:** Lost on restart; Redis for persistence later.

## Data Flow

### Deploy Flow

```
Push to main
    → GitHub Actions triggered
    → checkout, get SHA
    → SSH to DO
    → cd /opt/booty && git pull && pip install -e . && systemctl restart booty
    → (optional) Set SENTRY_RELEASE env from SHA
```

### Sentry Alert → Issue Flow

```
Sentry alert triggered
    → POST /webhooks/sentry (Observability agent)
    → Verify Sentry-Hook-Signature
    → Parse: severity, fingerprint, event URL, contexts
    → Filter: severity >= threshold? fingerprint not in cooldown?
    → Create GitHub issue (agent:builder, severity, breadcrumbs, release)
    → Update cooldown store
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Sentry | SDK (outbound) + Webhook (inbound) | DSN from env; webhook secret from env |
| GitHub | REST API via PyGithub | Same as Builder; issue creation |
| DigitalOcean | SSH | deploy.sh; workflow needs SSH key secret |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| main.py ↔ observability | Import route, call handler | Same app; no new process |
| observability ↔ github | PyGithub client | Shared client or new; minimal config |

## Sources

- Booty codebase — FastAPI, builder, verifier structure
- Sentry docs — webhook, SDK init
- deploy.sh — existing deploy flow

---
*Architecture research for: v1.3 Observability*
*Researched: 2026-02-15*
