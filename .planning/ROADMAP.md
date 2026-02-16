# Roadmap: Booty — Milestone v1.5 Security Agent

**Status:** ○ In progress
**Phases:** 18–21
**Requirements:** 17 (SEC-01 to SEC-17)

## Overview

The Security Agent is a merge veto authority. It runs on pull_request events, publishes the `booty/security` check, blocks merges on secrets and high/critical vulnerabilities, and escalates permission-surface changes to the Release Governor. Decision model: PASS, FAIL, ESCALATE.

## Phases

### Phase 18: Security Foundation & Check

**Goal:** Config schema, Security module skeleton, pull_request webhook, booty/security check.

**Requirements:** SEC-01, SEC-02, SEC-12, SEC-13, SEC-14, SEC-15, SEC-16

**Depends on:** Nothing

**Success criteria:**
1. SecurityConfig in BootyConfigV1 (enabled, fail_severity, sensitive_paths); unknown keys fail
2. SECURITY_ENABLED, SECURITY_FAIL_SEVERITY env overrides applied
3. pull_request opened/synchronize triggers Security pipeline
4. booty/security check published (queued → in_progress → completed)
5. Clear check titles (secret detected, vulnerability, workflow modified)

---

### Phase 19: Secret Leakage Detection

**Goal:** Scan changed files for secrets with gitleaks (or trufflehog); FAIL + annotate.

**Requirements:** SEC-03, SEC-04, SEC-17

**Depends on:** Phase 18

**Success criteria:**
1. Changed files only scanned (diff-based)
2. Secret detected → check FAIL, file+line annotations, cap 50
3. Check completes in under 60 seconds
4. Title "Security failed — secret detected"

---

### Phase 20: Dependency Vulnerability Gate

**Goal:** Auto-detect ecosystem from lockfiles; run audit; FAIL on severity >= HIGH.

**Requirements:** SEC-05, SEC-06, SEC-07

**Depends on:** Phase 18

**Success criteria:**
1. Lockfile detection: pip (requirements*.txt, pyproject.toml), npm (package-lock.json), composer (composer.lock), cargo (Cargo.lock)
2. Correct audit tool invoked per ecosystem
3. FAIL only on severity >= HIGH; low/medium ignored
4. Title "Security failed — critical vulnerability" when failed

---

### Phase 21: Permission Drift & Governor Integration

**Goal:** Sensitive paths → ESCALATE; persist override; Governor consumes.

**Requirements:** SEC-08, SEC-09, SEC-10, SEC-11

**Depends on:** Phase 18

**Success criteria:**
1. Sensitive paths matched (default: .github/workflows/**, infra/**, terraform/**, helm/**, k8s/**, iam/**, auth/**, security/**)
2. Touched → ESCALATE (not FAIL); title "Security escalated — workflow modified"
3. Override persisted: risk_override=HIGH, reason=permission_surface_change, sha
4. Governor reads override for head_sha before compute_decision; uses HIGH when present
5. PR is not blocked — only deploy risk escalated

---

## Milestone Summary

**Key decisions:**
- gitleaks preferred for secrets; trufflehog acceptable
- fail_severity: high (configurable)
- ESCALATE does not block merge; Governor handles deploy gating
- Security runs in parallel with Verifier (different check)

**Technical notes:**
- Security module: `src/booty/security/`
- Governor integration: Security writes to `.booty/state/security_overrides.json` or similar; Governor reads before risk computation
- Config loaded from repo .booty.yml (same as Governor)

---
*Last updated: 2026-02-16 — milestone v1.5 roadmap created*
