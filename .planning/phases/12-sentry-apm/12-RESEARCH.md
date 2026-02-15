# Phase 12: Sentry APM - Research

**Researched:** 2026-02-15
**Domain:** Sentry Python SDK, FastAPI error tracking, release correlation
**Confidence:** HIGH

## Summary

Sentry SDK for Python (`sentry-sdk`) provides first-class FastAPI integration via `FastApiIntegration` and `StarletteIntegration`. Initialize with `sentry_sdk.init()` before app creation; configure DSN, release, environment, and sample_rate from env vars. Use `traces_sample_rate=0` for errors-only. For conditional init: call `sentry_sdk.init()` only when DSN is present; production without DSN should fail startup per 12-CONTEXT. Manual capture via `sentry_sdk.capture_exception()` for handled failures (job pipeline crash, verifier crash). Release and environment are standard init params; deploy provides them via env (release.env).

**Primary recommendation:** Use sentry-sdk with FastAPI/Starlette integrations; init at earliest app startup; release/env from env; capture_exception in job and verifier exception handlers.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sentry-sdk | ≥2.0 | Error tracking, breadcrumbs | Official Python SDK; FastAPI integration built-in |

### Integration
| Integration | Purpose | When to Use |
|-------------|---------|-------------|
| FastApiIntegration | Request context, unhandled exception capture | Always for FastAPI apps |
| StarletteIntegration | ASGI middleware, request spans | Paired with FastAPI (Starlette base) |

**Installation:**
```bash
pip install sentry-sdk
# or in pyproject.toml: "sentry-sdk"
```

## Architecture Patterns

### Init Order
- Call `sentry_sdk.init()` **before** creating the FastAPI app
- Ensures all requests and exceptions are captured from first request
- In Booty: init in lifespan startup, before any routes handle traffic

### Init Configuration (12-CONTEXT aligned)
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

# DSN from env; release, environment from env (deploy sets SENTRY_RELEASE, SENTRY_ENVIRONMENT)
sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    release=os.environ.get("SENTRY_RELEASE") or None,  # None when missing (local dev)
    environment=os.environ.get("SENTRY_ENVIRONMENT") or "development",
    sample_rate=float(os.environ.get("SENTRY_SAMPLE_RATE", "1.0")),
    traces_sample_rate=0,  # Errors only this phase
    integrations=[
        StarletteIntegration(transaction_style="endpoint"),
        FastApiIntegration(transaction_style="endpoint"),
    ],
)
```

### Conditional Init (12-CONTEXT)
- **Production + no DSN** → `sys.exit(1)` (fail startup)
- **Non-production + no DSN** → skip init, log once, app runs normally
- **DSN present** → init with full config

### Manual Capture
```python
# In exception handler
except Exception as e:
    sentry_sdk.capture_exception(e)
    # optional: sentry_sdk.set_tag("job_id", job.job_id)
```

### Anti-Patterns to Avoid
- **Init after app creation:** Middleware won't capture early errors
- **Setting release to placeholder when unknown:** Pollutes Sentry grouping; use None/omit
- **traces_sample_rate=1.0 when errors-only:** CONTEXT says skip performance tracing this phase

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Error aggregation | Custom log pipeline | sentry-sdk | Grouping, fingerprinting, release correlation |
| Request context | Manual middleware | FastApiIntegration | Request URL, method, params auto-attached |
| Breadcrumbs | Manual event buffer | SDK default (max_breadcrumbs) | Structlog can add via Sentry integration; default sufficient |

## Common Pitfalls

### Pitfall 1: DSN in wrong env file
**What goes wrong:** DSN in release.env (deploy-written) gets overwritten; or DSN committed
**Why:** CONTEXT mandates DSN in secrets.env (separate from release.env)
**How to avoid:** Document that DSN lives in /etc/booty/secrets.env; deploy does NOT write it
**Warning signs:** deploy.sh writing SENTRY_DSN

### Pitfall 2: Release set to "unknown" or placeholder
**What goes wrong:** All local/dev events group under one fake release
**Why:** 12-CONTEXT: "When SHA unknown: skip release — placeholders pollute Sentry"
**How to avoid:** Pass `release=None` when SENTRY_RELEASE env is missing
**Warning signs:** `release="development"` or similar

### Pitfall 3: Init in wrong order
**What goes wrong:** First request errors not captured
**Why:** Init must run before app serves requests
**How to avoid:** Init in lifespan startup, first thing after configure_logging
**Warning signs:** Init in route or after app.add_middleware

## Code Examples

### FastAPI init (errors only)
```python
# main.py or dedicated sentry module
import os
import sys
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

def init_sentry():
    dsn = os.environ.get("SENTRY_DSN")
    environment = os.environ.get("SENTRY_ENVIRONMENT") or "development"
    is_production = environment.lower() in ("production", "prod")

    if not dsn:
        if is_production:
            get_logger().error("Sentry disabled — production requires DSN; refusing to start")
            sys.exit(1)
        get_logger().info("Sentry disabled — no DSN configured", environment=environment)
        return

    sentry_sdk.init(
        dsn=dsn,
        release=os.environ.get("SENTRY_RELEASE") or None,
        environment=environment,
        sample_rate=float(os.environ.get("SENTRY_SAMPLE_RATE", "1.0")),
        traces_sample_rate=0,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )
```

### capture_exception in job handler
```python
except Exception as e:
    logger.error("pipeline_exception", ...)
    sentry_sdk.capture_exception(e)
    # ... existing post_failure_comment
```

## Sources

### Primary (HIGH confidence)
- /getsentry/sentry-python — init, FastAPI integration, capture_exception, sample_rate
- 12-CONTEXT.md — implementation decisions (release, DSN, env behavior)

### Metadata
**Confidence:** HIGH — Context7 + official Sentry docs; 12-CONTEXT provides locked decisions
**Research date:** 2026-02-15
**Valid until:** ~30 days (stable SDK)
