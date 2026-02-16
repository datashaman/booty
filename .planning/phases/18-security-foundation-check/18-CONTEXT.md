# Phase 18: Security Foundation & Check - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Config schema (SecurityConfig), Security module skeleton, pull_request webhook wiring, and booty/security check lifecycle (queued → in_progress → completed). Actual scanning (secrets, vulns, permission drift) is Phases 19–21. This phase delivers the plumbing and structure for downstream phases.

</domain>

<decisions>
## Implementation Decisions

### Check titles and states
- **Queued:** Generic title (e.g. "Booty Security"), summary like "Queued"
- **In progress:** Same title as queued; summary "Scanning for secrets and vulnerabilities…"
- **Pass (no findings):** Short/neutral title — "Security check complete" or "Security OK"
- **Pass summary:** For Phases 19+, detailed — "Secret scan: clean. Dependency audit: clean." Phase 18 uses generic wording (see Phase 18 baseline below)

### Config behavior (absent or misconfigured)
- **Security block absent:** Enabled by default — Security runs unless `security: enabled: false`
- **Unknown keys in security block:** Fail only for Security — Security skips; Verifier and other features still run
- **Env vs file precedence:** Env wins — operators can override config at deploy time (SECURITY_ENABLED, SECURITY_FAIL_SEVERITY)
- **Default fail_severity:** HIGH — fail on high/critical only when omitted

### Trigger coverage
- **Actions:** opened, synchronize, reopened — mirror Verifier
- **Deduplication:** pr_number + head_sha (same as Verifier)
- **Cancel on new push:** Yes — cancel in-progress, enqueue new run when synchronize with new SHA
- **Scope:** Every PR gets booty/security (merge veto applies to all, not just agent PRs)

### Phase 18 baseline behavior
- **Pipeline content:** Minimal scaffold — create check → in_progress → load config, validate → complete success
- **Pass summary (Phase 18):** Generic — e.g. "Security check complete — no scanners configured" or "Foundation ready" (detailed scanner lines come in Phases 19–21)
- **Config validation:** Validate security block when present; fail on unknown keys (Security skips, rest of config loads)
- **Module skeleton:** Full structure — SecurityConfig schema + skeleton functions/hooks for secrets, vulns, permissions (empty for now; filled in Phases 19–21)

### Claude's Discretion
- Exact wording for "Booty Security" vs "Security" vs similar
- Precise pass title choice ("Security check complete" vs "Security OK")
- Skeleton function signatures and hook naming
- How to isolate Security config validation failure from top-level BootyConfig load

</decisions>

<specifics>
## Specific Ideas

- Mirror Verifier patterns for triggers, dedup, and cancel-on-push — consistency across agents
- Pass summary structure will evolve: Phase 18 generic; Phases 19+ add scanner-specific lines

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---
*Phase: 18-security-foundation-check*
*Context gathered: 2026-02-16*
