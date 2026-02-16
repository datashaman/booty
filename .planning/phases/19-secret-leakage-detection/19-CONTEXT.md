# Phase 19: Secret Leakage Detection - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Scan changed files in a PR for secrets using gitleaks or trufflehog. When secrets are detected: FAIL the booty/security check, annotate file+line, cap 50 annotations. Complete in under 60 seconds (target). This phase does not include permission drift or sensitive_paths — that's Phase 21.

</domain>

<decisions>
## Implementation Decisions

### Tool choice & fallback
- Prefer gitleaks; allow config override to force trufflehog (e.g. `secret_scanner: gitleaks | trufflehog` in .booty.yml)
- If chosen tool binary missing → try the other tool
- If both missing → FAIL with clear message ("Secret scanner not found")
- Configurable per repo

### Annotation cap behavior
- When >50 findings: prioritize by severity when available; otherwise by confidence; then by file path
- Summary when capped: include "and N more" in check summary
- Check summary: include short summary (e.g. "3 secrets in 2 files")
- Order annotations: severity → file path → line number

### Scan scope & exclusions
- Lockfiles/manifests: default exclude (package-lock.json, pip.lock, Cargo.lock, etc.) with configurable override to include
- Generated/binary files: skip binaries and typical generated patterns (dist/, *.min.js, etc.)
- sensitive_paths: do not use for Phase 19 — scan all changed files; sensitive_paths is Phase 21 only
- Allowlist: config option `secret_scan_exclude: [...]` for repo-specific exclusions (e.g. test fixtures)

### Failure & timeout handling
- Scanner crash/unexpected exit: treat as "scan incomplete", FAIL
- Approaching 60s: let scan run to completion; 60s is target, not hard cutoff
- Timeout mid-scan (if enforced): FAIL with partial annotations if any
- Empty diff (no changed files): skip scan, mark complete, PASS

### Claude's Discretion
- Exact list of default lockfile/manifest patterns to exclude
- Exact generated/binary patterns to skip
- Config key naming (secret_scanner vs secret_scanner_tool, etc.)
- "Scan incomplete" vs "Scanner failed" wording

</decisions>

<specifics>
## Specific Ideas

No specific references — open to standard gitleaks/trufflehog usage patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 19-secret-leakage-detection*
*Context gathered: 2026-02-16*
