# Stack Research: Control-Plane Event Infrastructure

**Domain:** GitHub webhook event routing, dedup, and delivery semantics for multi-agent pipelines
**Researched:** 2026-02-17
**Confidence:** HIGH

## GitHub Webhook Delivery Semantics (Verified)

### Key Facts

| Aspect | Behavior | Source |
|--------|----------|--------|
| Auto-retry on failure | **None** — GitHub does NOT automatically redeliver failed webhooks | [GitHub docs: Handling failed webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries) |
| Response timeout | 10 seconds — server must respond with 2XX or delivery marked failed | [Best practices](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks) |
| X-GitHub-Delivery | Unique per delivery; **same on manual redelivery** — use for replay protection | [Best practices](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks) |
| Ordering | No guarantee — out-of-order delivery possible | Inferred from docs |

### Implications for Dedup Design

1. **At-least-once on manual redeliver:** User can redeliver from GitHub UI/API; same `X-GitHub-Delivery` — must dedup.
2. **Network retries:** Client retries (e.g., 5xx) can cause duplicate deliveries with same delivery_id.
3. **Respond within 10s:** Enqueue asynchronously; process in workers. Booty already does this.

## Recommended Stack Additions (Minimal)

**Existing stack is sufficient.** No new libraries needed. Changes are architectural:

| Area | Current | Recommendation |
|------|---------|----------------|
| Event model | Ad-hoc branches in webhooks.py | Canonical internal event types (see ARCHITECTURE.md) |
| Dedup keys | Inconsistent (delivery_id vs pr_number:head_sha, some without repo) | Standardize (see FEATURES.md) |
| Cancellation | Reviewer only | Extend Verifier/Security with cooperative cancel |

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Message queue (RabbitMQ, SQS) for webhooks | Adds infra; in-memory queue + fast 202 response is sufficient for Booty scale | Current asyncio.Queue |
| Distributed lock for promotion | Overkill for single-instance; deterministic "only Verifier promotes" suffices | Single promote point + reviewer_check_success |

## Sources

- [GitHub: Handling failed webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries)
- [GitHub: Best practices for webhooks](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks)
- [Idempotent webhook handling (Averagedevs, Hookdeck, Inngest)](https://www.averagedevs.com/blog/reliable-webhook-delivery-idempotent-secure)

---
*Stack research for: v1.10 Pipeline Correctness*
*Researched: 2026-02-17*
