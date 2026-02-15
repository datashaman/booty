# Phase 13: Observability Agent - Research

**Researched:** 2026-02-15
**Domain:** Sentry webhooks, HMAC verification, GitHub issue creation, Python/FastAPI
**Confidence:** HIGH

## Summary

Phase 13 implements a Sentry-alert-to-GitHub-issue pipeline: receive webhooks from Sentry when error alert rules fire, verify HMAC signature, filter by severity and dedup/cooldown, then create GitHub issues with `agent:builder` for Builder intake. The Sentry Integration Platform provides `event_alert` webhooks with rich payloads (level, fingerprint, exception, stack trace, metadata) — no API fetch needed for issue creation. The existing `webhooks.py` pattern (raw body HMAC, FastAPI Request) applies directly; PyGithub creates issues. Use `issue_id` or `hashes` for dedup; in-memory cooldown per fingerprint suffices for v1.

**Primary recommendation:** Use raw request body for HMAC (like GitHub webhook); filter on `Sentry-Hook-Resource: event_alert`; use `data.event.issue_id` for dedup; `data.event.level` for severity filtering; build issue body from `data.event` (level, metadata, exception, web_url, release, tags).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hmac + hashlib | stdlib | HMAC-SHA256 for Sentry-Hook-Signature | Same as GitHub verify_signature; constant-time compare |
| FastAPI | existing | POST route, Request.body() | Already used for /webhooks/github |
| PyGithub | existing | repo.create_issue() | Already used for PR creation, comments |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | existing | Retry GitHub API calls | 3 attempts, exponential backoff per CONTEXT |
| pydantic | existing | Settings, optional schema | Config validation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw body HMAC | json.dumps(parsed) | Sentry docs show both; raw body matches GitHub, safer |
| in-memory cooldown | Redis | OBSV-10 deferred; in-memory fine for v1 |

**Installation:** No new deps. Reuse existing stack.

## Architecture Patterns

### Recommended Project Structure

```
src/booty/
├── webhooks.py          # Add /webhooks/sentry route
├── observability/      # NEW: optional module
│   ├── __init__.py
│   ├── sentry_webhook.py   # verify, parse, filter
│   ├── filters.py          # severity, dedup, cooldown
│   └── issue_creator.py    # build body, create GitHub issue
├── config.py           # Add SENTRY_WEBHOOK_SECRET, OBSV_* settings
```

Or keep everything in `webhooks.py` + `observability/` if it stays under ~150 lines total. Splitting by concern preferred if >200 LOC.

### Pattern 1: Webhook Verify-Filter-Act

**What:** Read raw body → verify HMAC → parse JSON → filter (resource, severity, dedup, cooldown) → side effect (create issue).
**When to use:** All Sentry webhook handling.
**Example:** Mirror `github_webhook` flow: `payload_body = await request.body()` before any parsing; verify; then `json.loads()`; filter; create issue.

### Pattern 2: HMAC Verification (Sentry)

**What:** HMAC-SHA256 of raw body, key = client secret, compare to `Sentry-Hook-Signature` (case-insensitive header).
**When to use:** Every Sentry webhook request.
**Example:**
```python
# Header: Sentry-Hook-Signature (docs show lowercase in examples)
sig_header = request.headers.get("Sentry-Hook-Signature") or request.headers.get("sentry-hook-signature")
digest = hmac.new(secret.encode("utf-8"), payload_body, hashlib.sha256).hexdigest()
if not hmac.compare_digest(digest, sig_header):
    raise HTTPException(401, detail="invalid_signature")
```

**Source:** Sentry Integration Platform docs, Context7 /getsentry/sentry-docs

### Anti-Patterns to Avoid

- **Parse before verify:** Never `request.json()` before HMAC; always `request.body()` first.
- **Skip verification in dev:** CONTEXT says use dummy secret; no exception for unverified webhooks.
- **Full message in title:** CONTEXT: title must not include full message (volatile, breaks dedup).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HMAC verification | Custom crypto | hmac.compare_digest() | Constant-time, stdlib |
| GitHub issue creation | REST client | PyGithub repo.create_issue() | Already in stack |
| Retry with backoff | Manual loops | tenacity | Already used in codebase |

## Common Pitfalls

### Pitfall 1: Body for HMAC
**What goes wrong:** Using parsed JSON string for HMAC when Sentry signs raw bytes; verification fails.
**Why it happens:** FastAPI/Starlette consume body; must get raw bytes before parsing.
**How to avoid:** `payload_body = await request.body()` first; verify; then `json.loads(payload_body)`.
**Warning signs:** "Signature verification fails" when payload is valid.

### Pitfall 2: event_alert vs metric_alert
**What goes wrong:** Handling metric_alert (aggregate thresholds) when we want event_alert (individual errors).
**Why it happens:** Both use same webhook URL; differ by `Sentry-Hook-Resource` header.
**How to avoid:** Check `Sentry-Hook-Resource == "event_alert"`; ignore metric_alert.
**Warning signs:** Payload structure doesn't match (no data.event, no exception).

### Pitfall 3: Missing fingerprint for dedup
**What goes wrong:** Creating duplicate GitHub issues for same Sentry issue.
**Why it happens:** Sentry sends one webhook per event; multiple events group to one issue.
**How to avoid:** Dedup by `data.event.issue_id` (Sentry's issue ID = one per fingerprint group).
**Warning signs:** Same error pattern creates many issues.

## Code Examples

### Sentry Webhook Signature Verification
```python
import hmac
import hashlib

def verify_sentry_signature(payload_body: bytes, secret: str, signature_header: str | None) -> None:
    if not signature_header:
        raise HTTPException(401, detail="invalid_signature")
    digest = hmac.new(
        secret.encode("utf-8"), payload_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(digest, signature_header.strip()):
        raise HTTPException(401, detail="invalid_signature")
```
Source: Sentry docs, GitHub webhooks.py pattern

### event_alert Payload Structure (Key Fields)
```python
# data.event from Sentry issue alert webhook
{
    "level": "error",           # fatal, error, warning, info, debug
    "issue_id": "1117540176",   # Use for dedup
    "hashes": ["29f7ff..."],    # Alternative dedup key
    "fingerprint": ["{{ default }}"],
    "web_url": "https://sentry.io/.../issues/123/events/...",
    "url": "https://sentry.io/api/0/projects/.../events/.../",
    "metadata": {"filename": " ", "type": "ReferenceError", "value": "heck is not defined"},
    "exception": {"values": [{"type": "ReferenceError", "value": "...", "stacktrace": {"frames": [...]}}]},
    "culprit": "?()",
    "release": null,
    "tags": [["level", "error"], ["environment", "production"]],
}
```
Source: https://docs.sentry.io/organization/integrations/integration-platform/webhooks/issue-alerts

### GitHub Issue Creation (PyGithub)
```python
from github import Github
g = Github(settings.GITHUB_TOKEN)
repo = g.get_repo("owner/repo")  # From TARGET_REPO_URL
issue = repo.create_issue(title="...", body="...", labels=["agent:builder"])
```
Source: PyGithub, existing Booty usage

## State of the Art

| Old Approach | Current Approach | Impact |
|-------------|------------------|--------|
| Poll Sentry API | Webhook push | Lower latency, no rate limits (per research) |
| No signature verify | HMAC-SHA256 | Prevents spoofed alerts |
| Create issue per event | Dedup + cooldown | Prevents alert storms |

## Open Questions

1. **Breadcrumbs in payload:** Example payload didn't include `breadcrumbs`; if present, use per CONTEXT (last 8, truncate 160 chars, drop debug). If absent, omit from issue body.
2. **Raw body vs JSON string for HMAC:** Sentry Python example used `json.dumps(request.body)` (parsed body). Doc note says "raw request body." Recommend raw bytes to match GitHub pattern and avoid encoding ambiguity.

## Sources

### Primary (HIGH confidence)
- Context7 /getsentry/sentry-docs — webhook signature, issue alert structure
- https://docs.sentry.io/organization/integrations/integration-platform/webhooks/issue-alerts — full payload example
- Existing webhooks.py, config.py, main.py

### Secondary (MEDIUM confidence)
- .planning/research/ARCHITECTURE.md, PITFALLS.md — prior Booty research
- CONTEXT.md — locked decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing codebase, Sentry official docs
- Architecture: HIGH — mirrors GitHub webhook pattern
- Pitfalls: HIGH — documented in Sentry docs and CONTEXT

**Research date:** 2026-02-15
**Valid until:** 60 days (Sentry webhook API stable)
