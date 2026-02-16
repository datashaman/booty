# Security Agent

Merge veto authority for secrets, vulnerabilities, and permission drift. Runs on pull_request events, publishes the `booty/security` check. Decision model: PASS, FAIL, ESCALATE.

## Overview

The Security Agent runs in parallel with the Verifier. It:

- **Secret scan**: Scans changed files for secrets (gitleaks); FAIL with annotations
- **Dependency audit**: Auto-detects lockfiles (pip, npm, composer, cargo); FAIL on severity ≥ HIGH
- **Permission drift**: When sensitive paths touched → ESCALATE (not FAIL); persists override for Governor

ESCALATE does not block merge — it escalates deploy risk to HIGH for the Release Governor.

## Configuration

Add a `security` block to `.booty.yml` (schema_version 1). **Optional** — when absent, Security runs with defaults (enabled, gitleaks, default sensitive_paths).

```yaml
security:
  enabled: true
  fail_severity: high
  sensitive_paths:
    - ".github/workflows/**"
    - "infra/**"
    - "terraform/**"
    - "helm/**"
    - "k8s/**"
    - "iam/**"
    - "auth/**"
    - "security/**"
  secret_scanner: gitleaks  # or trufflehog
  secret_scan_exclude: []   # e.g. ["tests/fixtures/**"] for fixture files with placeholders
```

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | true | Master switch |
| `fail_severity` | high | Severity threshold: low, medium, high, critical |
| `sensitive_paths` | workflows, infra, terraform, etc. | Pathspecs for permission drift escalation |
| `secret_scanner` | gitleaks | gitleaks or trufflehog |
| `secret_scan_exclude` | [] | Path patterns to exclude from secret scan |

### Environment overrides

| Variable | Maps to |
|----------|---------|
| `SECURITY_ENABLED` | enabled (1/true/yes) |
| `SECURITY_FAIL_SEVERITY` | fail_severity |

## How it runs

1. **Trigger**: `pull_request` opened or synchronize (same as Verifier)
2. **Config**: Loaded from `.booty.yml` at PR head (via GitHub API)
3. **Pipeline**: Secret scan → dependency audit → permission drift
4. **Check**: `booty/security` (queued → in_progress → completed)

## Check outcomes

| Outcome | Conclusion | Title |
|---------|------------|-------|
| Pass | success | Security check complete |
| Secret detected | failure | Security failed — secret detected |
| High/critical vuln | failure | Security failed — critical vulnerability |
| Sensitive path touched | success (ESCALATE) | Security escalated — workflow modified |

## Governor integration

When sensitive paths are touched, Security persists an override to `security_overrides.json`. The Release Governor reads this before computing risk and uses `risk_class=HIGH` when present — deploy gating is escalated even if path-based risk would be lower.

## Requirements

- **gitleaks** (or trufflehog) installed for secret scanning
- **pip-audit**, **npm audit**, **composer audit**, **cargo audit** for dependency ecosystems in use

Without the scanner binary, secret scan returns `scan_ok=False` and the check fails with an error message.

## GitHub App & Actions

**No changes needed.** Security uses the same setup as the Verifier:

- **Events:** Same `pull_request` webhook (opened, synchronize, reopened)
- **Permissions:** Same Checks (R/W), Contents (R), Pull requests (R)
- **GitHub Actions:** Security runs server-side in Booty when webhooks arrive — not in workflows. No `.github/workflows/*.yml` changes required.

If Verifier works, Security works with the same App configuration.

## Booty repo config

The booty repo can add an explicit `security` block to `.booty.yml` after the Security Agent is deployed. Until then, Security uses defaults when the block is absent. Example:

```yaml
security:
  enabled: true
  fail_severity: high
  secret_scanner: gitleaks
```

*Note: The `security` key requires BootyConfigV1 with the security field (milestone v1.5+). Older deployments will reject configs with `security` — omit the block for backward compatibility.*

---

*See [github-app-setup.md](github-app-setup.md) for webhook and App setup.*
