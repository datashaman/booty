# Feature Research

**Domain:** Observability — deploy automation, Sentry APM, alert-to-issue pipeline
**Researched:** 2026-02-15
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Deploy on merge | CI/CD standard; no manual SSH | LOW | Workflow on push to main; reuse deploy.sh |
| Error tracking with stack traces | Core APM value | LOW | sentry-sdk auto-captures |
| Release/SHA correlation | Know which deploy caused errors | LOW | `release` = git SHA in sentry_sdk.init |
| Webhook signature verification | Security baseline | LOW | HMAC-SHA256; Sentry docs specify |
| Filter by severity | Avoid noise from low-severity | MEDIUM | Parse Sentry payload; configurable threshold |
| Dedup by fingerprint | One issue per error pattern | MEDIUM | Sentry `grouping_fingerprint` or equivalent |
| Cooldown per fingerprint | Prevent alert storm | MEDIUM | In-memory or lightweight store |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Auto-created GitHub issues with agent:builder | Closes loop; Builder picks up automatically | MEDIUM | Same label as Builder webhook |
| Repro breadcrumbs in issue body | Gives Builder context to fix | LOW | Copy from Sentry event |
| Environment + release in issue | Correlate with deploy | LOW | Tag body or labels |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|--------------|
| Create issue for every Sentry event | "Don't miss anything" | Alert storm, duplicate issues | Filter + dedup + cooldown first |
| Real-time Slack/Discord | Visibility | Diverges from GitHub-centric model | Stick to issues |
| Custom dashboard for observability | "Need to see metrics" | Scope creep; CLI/GitHub are interfaces | Use Sentry UI |

## Feature Dependencies

```
Deploy Automation
    └── (standalone; no deps)

Sentry APM
    └── (standalone; release from deploy helps)

Observability Agent
    ├── requires → Sentry APM (DSN, release format)
    ├── requires → Webhook endpoint (new route)
    └── requires → PyGithub (already present)
```

### Dependency Notes

- **Observability Agent requires Sentry APM:** Need DSN, release format; app must send events for correlation.
- **Deploy automation is independent:** Can ship first; enables SHA-based release tagging.

## MVP Definition

### Launch With (v1.3)

- [ ] GitHub Actions workflow triggers on push to main → SSH deploy
- [ ] Sentry SDK in FastAPI app with `release` = git SHA, `environment` = prod
- [ ] Observability agent: Sentry webhook route, HMAC verify, filter (severity, dedup, cooldown)
- [ ] Create GitHub issue with agent:builder label, severity, repro breadcrumbs, release/SHA

### Add After Validation (v1.x)

- [ ] Multiple environments (staging vs prod)
- [ ] Observability agent persistence (cooldown across restarts)

### Future Consideration (v2+)

- [ ] Dashboard for observability metrics
- [ ] Multiple Sentry projects → routing

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Deploy automation | HIGH | LOW | P1 |
| Sentry APM + release | HIGH | LOW | P1 |
| Webhook + verify | HIGH | LOW | P1 |
| Filter + dedup + cooldown | HIGH | MEDIUM | P1 |
| Issue creation | HIGH | LOW | P1 |
| Breadcrumbs in issue | MEDIUM | LOW | P2 |

## Sources

- Sentry docs — webhook payload, signature
- Booty PROJECT.md — Active (v1.3) requirements
- deploy.sh — existing deploy flow

---
*Feature research for: v1.3 Observability*
*Researched: 2026-02-15*
