# Pitfalls Research

**Domain:** Observability — deploy automation, Sentry APM, alert-to-issue pipeline
**Researched:** 2026-02-15
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Skipping Webhook Signature Verification

**What goes wrong:** Attacker posts fake Sentry payloads → creates spam/issues or triggers unintended behavior.

**Why it happens:** Dev treats webhook as "internal" or prioritizes speed over security.

**How to avoid:** Always verify `Sentry-Hook-Signature` with HMAC-SHA256 before processing. Use constant-time comparison.

**Warning signs:** No verification in initial webhook handler; secret stored in code.

**Phase to address:** Observability agent phase (webhook route).

---

### Pitfall 2: Alert Storm — No Dedup or Cooldown

**What goes wrong:** Same error fires 100 times → 100 GitHub issues → Builder overwhelmed.

**Why it happens:** Sentry sends one webhook per triggered rule per event; no built-in dedup at receiver.

**How to avoid:** Dedup by `grouping_fingerprint` (or equivalent); cooldown per fingerprint (e.g., 1 hour). Filter by severity.

**Warning signs:** "Create issue for every webhook" in requirements without filtering.

**Phase to address:** Observability agent phase (filter module).

---

### Pitfall 3: Release Not Set or Wrong Format

**What goes wrong:** Sentry shows "release: unknown" → can't correlate errors with deploy.

**Why it happens:** Forgetting to pass `release` to sentry_sdk.init(); or using app version instead of git SHA.

**How to avoid:** Set `release="booty@${GIT_SHA}"` at startup; CI exports GIT_SHA and deploy passes to app (env or systemd).

**Warning signs:** Sentry events without release; manual deploy doesn't set env.

**Phase to address:** Deploy automation + Sentry APM phase.

---

### Pitfall 4: SSH Key Exposure in Workflow

**What goes wrong:** Private key committed; or logged in step output.

**Why it happens:** Copy-paste from examples; debug `echo $SSH_KEY`.

**How to avoid:** Use GitHub Actions secrets; never echo secrets; use `appleboy/ssh-action` or pass via env to `ssh`.

**Warning signs:** Key in workflow file; run step that prints env.

**Phase to address:** Deploy automation phase.

---

### Pitfall 5: Webhook Secret Mismatch

**What goes wrong:** Sentry configured with one secret; Booty expects another → all webhooks fail verify.

**Why it happens:** Env var typo; different secret in Sentry UI vs .env.

**How to avoid:** Document exact env name (e.g. SENTRY_WEBHOOK_SECRET); verify in dev with test webhook.

**Warning signs:** 401/403 on every webhook; "signature invalid" in logs.

**Phase to address:** Observability agent phase.

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Sentry webhook | Using raw body for HMAC then parsing JSON again | Use raw bytes for HMAC; parse once after verify |
| GitHub issue | Missing agent:builder label | Builder won't pick up; label is required |
| Deploy workflow | Running on every push (incl. PR) | Use `on.push.branches: [main]` |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Cooldown store unbounded | Memory growth over days | TTL + periodic cleanup or max size | Long-running process |
| Blocking Sentry in request path | Slow responses | Sentry SDK is async by default | If custom sync code |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging webhook payload | PII/exceptions in logs | Log only fingerprint, action; never full body |
| DSN in client code | DSN exposure | Server-only; never in frontend |

## "Looks Done But Isn't" Checklist

- [ ] **Deploy workflow:** Verify it actually runs on merge to main; check Actions tab
- [ ] **Sentry release:** Confirm Sentry UI shows release = git SHA for new events
- [ ] **Webhook:** Test with Sentry "Send Test" or curl with valid signature
- [ ] **Issue creation:** Check issue has agent:builder label; Builder picks it up
- [ ] **Cooldown:** Trigger same error twice; second should not create issue

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| No webhook verify | Observability agent | Unit test: invalid signature → 401 |
| Alert storm | Observability agent | Manual: fire same alert 2x → 1 issue |
| Release not set | Deploy + Sentry APM | Sentry UI shows release |
| SSH key exposure | Deploy automation | Audit workflow; no secrets in logs |
| Webhook secret mismatch | Observability agent | Doc env name; test webhook |

## Sources

- Sentry docs — signature verification
- GitHub Actions — secrets handling
- Booty deploy.sh — existing patterns

---
*Pitfalls research for: v1.3 Observability*
*Researched: 2026-02-15*
