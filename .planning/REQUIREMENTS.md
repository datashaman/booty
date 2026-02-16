# Requirements: Booty — Milestone v1.5 Security Agent

**Defined:** 2026-02-16
**Core Value:** A Builder agent that can take a GitHub issue and produce a working PR with tested code — the foundation everything else builds on.

## v1.5 Requirements

Security Agent: merge veto authority. Verifier answers "Does it work?" — Security answers "Could this harm us?"

### Secret Detection

- [ ] **SEC-01**: Security agent runs on `pull_request` opened and synchronize
- [ ] **SEC-02**: Security publishes required GitHub check `booty/security`
- [x] **SEC-03**: Security scans changed files only for secrets (gitleaks preferred; trufflehog acceptable)
- [x] **SEC-04**: When secret detected: check FAIL, annotate file+line, title "Security failed — secret detected", cap 50 annotations

### Dependency Vulnerability

- [x] **SEC-05**: Security auto-detects ecosystem via lockfiles (pip, npm, composer, cargo)
- [x] **SEC-06**: Security runs appropriate audit tool (pip-audit, npm audit, composer audit, cargo audit)
- [x] **SEC-07**: Security FAILs check only when severity >= HIGH; ignore low/medium

### Permission Drift

- [ ] **SEC-08**: Security watches sensitive paths (`.github/workflows/**`, `infra/**`, `terraform/**`, `helm/**`, `k8s/**`, `iam/**`, `auth/**`, `security/**`)
- [ ] **SEC-09**: When sensitive path touched: result ESCALATE (not FAIL), override deploy risk to HIGH, reason `permission_surface_change`
- [ ] **SEC-10**: Governor consumes Security risk override before deploy decisions
- [ ] **SEC-11**: Security does NOT fail PR on permission drift — only escalates to Governor

### Configuration

- [ ] **SEC-12**: Extend .booty.yml with `security` block: `enabled`, `fail_severity`, `sensitive_paths`
- [ ] **SEC-13**: Unknown keys in security block fail config load (extra='forbid')
- [ ] **SEC-14**: Env overrides: `SECURITY_ENABLED`, `SECURITY_FAIL_SEVERITY`

### Check UX

- [ ] **SEC-15**: Check name `booty/security`
- [ ] **SEC-16**: Clear titles only: "Security failed — secret detected", "Security failed — critical vulnerability", "Security escalated — workflow modified"

### Performance

- [x] **SEC-17**: Security check completes in under 60 seconds (diff-only scanning, parallelize when safe)

## Future Requirements

Deferred to later milestones.

- Persistent cooldown store (OBSV-10) — from v1.3
- Staging vs production deploy targets (DEPLOY-04)
- Rollback workflow (DEPLOY-05)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-remediation | Spec: no auto-remediation |
| Patch PRs | Spec: no patch PRs |
| Runtime security platform | Spec: no runtime security |
| ML risk scoring | Spec: no ML risk scoring |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-01 | 18 | Complete |
| SEC-02 | 18 | Complete |
| SEC-12 | 18 | Complete |
| SEC-13 | 18 | Complete |
| SEC-14 | 18 | Complete |
| SEC-15 | 18 | Complete |
| SEC-16 | 18 | Complete |
| SEC-03 | 19 | Complete |
| SEC-04 | 19 | Complete |
| SEC-17 | 19 | Complete |
| SEC-05 | 20 | Complete |
| SEC-06 | 20 | Complete |
| SEC-07 | 20 | Complete |
| SEC-08 | 21 | Pending |
| SEC-09 | 21 | Pending |
| SEC-10 | 21 | Pending |
| SEC-11 | 21 | Pending |

**Coverage:**
- v1.5 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-16*
*Last updated: 2026-02-16 after milestone v1.5 definition*
