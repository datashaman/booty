# Phase 18: Security Foundation & Check — Verification

**Verified:** 2026-02-16
**Status:** passed
**Score:** 5/5 must-haves

## Must-Have Verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | SecurityConfig in BootyConfigV1 (enabled, fail_severity, sensitive_paths); unknown keys fail | ✓ VERIFIED | src/booty/test_runner/config.py: SecurityConfig with extra="forbid"; BootyConfigV1.security; field_validator returns None on ValidationError. tests/test_security_config.py covers unknown keys rejection. |
| 2 | SECURITY_ENABLED, SECURITY_FAIL_SEVERITY env overrides applied | ✓ VERIFIED | apply_security_env_overrides in config.py; tests cover SECURITY_ENABLED and SECURITY_FAIL_SEVERITY. |
| 3 | pull_request opened/synchronize triggers Security pipeline | ✓ VERIFIED | webhooks.py: SecurityJob enqueued on opened/synchronize/reopened; security_queue.enqueue; no is_agent_pr filter. |
| 4 | booty/security check published (queued → in_progress → completed) | ✓ VERIFIED | security/runner.py: create_security_check_run (queued) → edit_check_run (in_progress) → edit_check_run (completed). checks.py: name="booty/security". |
| 5 | Clear check titles | ✓ VERIFIED | Phase 18 baseline: "Booty Security" (queued), "Scanning for secrets and vulnerabilities…" (in_progress), "Security check complete" / "Security check complete — disabled" / "Security check complete — no scanners configured" (completed). Phases 19–21 add specific titles (secret detected, vulnerability, workflow modified). |

## Artifacts Verified

- `src/booty/test_runner/config.py` — SecurityConfig, BootyConfigV1.security, apply_security_env_overrides ✓
- `src/booty/security/` — job.py, queue.py, runner.py, __init__.py ✓
- `src/booty/github/checks.py` — create_security_check_run ✓
- `src/booty/config.py` — security_enabled, SECURITY_WORKER_COUNT ✓
- `src/booty/webhooks.py` — pull_request → SecurityJob enqueue ✓
- `src/booty/main.py` — security_queue in lifespan ✓

## Human Verification

None required.

## Gaps

None.

---
*Phase: 18-security-foundation-check*
*Verification: passed*
