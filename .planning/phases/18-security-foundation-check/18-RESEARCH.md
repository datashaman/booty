# Phase 18: Security Foundation & Check - Research

**Researched:** 2026-02-16
**Domain:** GitHub Checks API, Pydantic config extension, pull_request webhook orchestration
**Confidence:** HIGH

## Summary

Phase 18 delivers the Security module plumbing: config schema, skeleton, pull_request webhook wiring, and booty/security check lifecycle. The codebase already implements equivalent patterns for Verifier (pull_request → VerifierQueue → check run) and Release Governor (BootyConfigV1 with ReleaseGovernorConfig). Security mirrors Verifier's architecture and config patterns from Governor.

**Primary recommendation:** Extend BootyConfigV1 with SecurityConfig (extra='forbid'); add security_enabled() and apply_security_env_overrides(); create SecurityQueue + SecurityJob mirroring VerifierQueue/VerifierJob; wire pull_request to enqueue Security jobs in parallel with Verifier; add github/checks.create_security_check_run and edit_security_check_run; implement security runner that creates check → in_progress → completed success.

## Standard Stack

### Core (existing)
| Component | Version | Purpose | Why Standard |
|----------|---------|---------|--------------|
| PyGithub | current | Checks API, repo contents | Already used for booty/verifier |
| Pydantic | v2 | Config schema | BootyConfigV1, ReleaseGovernorConfig |
| FastAPI | current | Webhooks | pull_request handler |

### No new libraries
Phase 18 reuses Verifier's GitHub App auth (GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY), PyGithub create_check_run/edit_check_run, and VerifierQueue-style async queue.

## Architecture Patterns

### Recommended Module Structure
```
src/booty/
├── security/
│   __init__.py      # SecurityJob, SecurityQueue exports
│   job.py           # SecurityJob dataclass (owner, repo_name, pr_number, head_sha, ...)
│   queue.py         # SecurityQueue (pr_number+head_sha dedup, mirror VerifierQueue)
│   runner.py        # process_security_job: create check → in_progress → load config → completed
│   config.py        # (optional) apply_security_env_overrides
├── github/
│   checks.py        # Extend: create_security_check_run, get_security_repo (reuse get_verifier_repo logic)
├── test_runner/
│   config.py        # SecurityConfig, BootyConfigV1.security
├── webhooks.py      # pull_request: also enqueue SecurityJob to security_queue
└── main.py          # security_queue in lifespan (like verifier_queue)
```

### Pattern 1: Config Block with extra='forbid'
**What:** SecurityConfig with model_config = ConfigDict(extra="forbid"); unknown keys fail.
**Example:** ReleaseGovernorConfig in test_runner/config.py (lines 70–106).
**Apply:** SecurityConfig: enabled, fail_severity (Literal["low","medium","high","critical"]), sensitive_paths list.

### Pattern 2: Env Override Helper
**What:** apply_security_env_overrides(config) → returns new config with SECURITY_ENABLED, SECURITY_FAIL_SEVERITY applied.
**Example:** apply_release_governor_env_overrides in test_runner/config.py (lines 109–146).
**Apply:** SECURITY_ENABLED (bool), SECURITY_FAIL_SEVERITY (str).

### Pattern 3: Check Run Lifecycle
**What:** queued → in_progress → completed (success|failure).
**Example:** verifier/runner.py create_check_run → edit_check_run(status="in_progress") → edit_check_run(conclusion, output).
**Apply:** Same flow for booty/security; check name "booty/security".

### Pattern 4: pull_request Multi-Agent Routing
**What:** One pull_request event can enqueue to multiple queues (Verifier, Security).
**Apply:** After Verifier enqueue block, add Security enqueue block; both use same payload extraction (owner, repo, pr_number, head_sha, installation_id). Security runs on every PR; no is_agent_pr filter for Security.

### Pattern 5: Config Validation Isolation
**What:** Security block unknown keys → Security skips; Verifier and Governor still run.
**Apply:** When loading .booty.yml for Security, catch ValidationError on security block parse; if SecurityConfig fails, Security skips this PR (or use try/except around config.security access). Top-level BootyConfigV1 load must NOT fail—only Security's use of the security block fails. Per CONTEXT: "Unknown keys in security block: Fail only for Security — Security skips."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|--------|-------------|-------------|-----|
| Check run creation | Custom HTTP | PyGithub repo.create_check_run | Same as Verifier |
| Auth for checks | PAT | GitHub App (existing) | Verifier uses same |
| Queue + workers | Custom | asyncio.Queue + VerifierQueue pattern | Proven |
| Config validation | Custom YAML | Pydantic model_validate | ReleaseGovernorConfig pattern |

## Common Pitfalls

### Pitfall 1: Blocking Verifier When Security Config Fails
**What goes wrong:** Top-level config load fails on security unknown keys, Verifier never runs.
**Why:** BootyConfigV1 has extra='forbid' at top level—adding security block with extra='forbid' on SecurityConfig is fine. But if security block has unknown keys, _parse_booty_config will fail when validating BootyConfigV1 if we add security: SecurityConfig. Need to parse security block separately or use a two-stage load: load BootyConfigV1 without security, then optionally validate security block. Per CONTEXT: "Fail only for Security" — so Security skips, rest runs. Implementation: validate full config normally; if ValidationError is in security block, catch and set security=None for top-level, but that would require BootyConfigV1 to allow security to be optional and validation to be lenient. Better: Security block validation happens only when Security reads config—Verifier and others use load_booty_config_from_content as today. So we need: BootyConfigV1.security: SecurityConfig | None = None. When parsing, if "security" key exists, validate SecurityConfig. If SecurityConfig validation fails (unknown keys), the whole BootyConfigV1 parse fails with extra='forbid'. The CONTEXT says "Unknown keys in security block fail config load" for SEC-13 but also "Fail only for Security — Security skips". Those conflict slightly. Reading again: "Unknown keys in security block: Fail only for Security — Security skips; Verifier and other features still run." So the config load for Verifier must succeed even when security block has unknown keys. That implies: we need to parse the security block in a way that doesn't fail top-level. Options: (a) security block validated lazily when Security runs; (b) two-stage parse: load without security, then try security; (c) SecurityConfig validation fails → we catch and treat as "security disabled for this repo". CONTEXT: "Config validation: Validate security block when present; fail on unknown keys (Security skips, rest of config loads)". So: validate security block when present; if unknown keys → Security skips. The rest of config (Verifier, Governor) still loads. That means we need to NOT fail BootyConfigV1 when security has unknown keys. So BootyConfigV1.security could be Optional[SecurityConfig] but we need a separate validation step: when loading, if "security" in data, try SecurityConfig.model_validate(data["security"]). If that raises, we still return BootyConfigV1 with security=None (and maybe a flag or we just skip Security). So the parse logic: parse top-level; for security key, try SecurityConfig.model_validate; on ValidationError, set security=None and perhaps log. BootyConfigV1 would have security: SecurityConfig | None = None, and we'd need a custom validator or a pre-parse step. Easier: use a Union or a wrapper. Actually the simplest: in _parse_booty_config, when we have schema_version 1, we parse the rest. For the "security" key, we do a try/except: try SecurityConfig.model_validate(data.get("security")); except ValidationError: security=None. But then BootyConfigV1.model_validate(data) would fail because we're passing data with "security" that might have extra keys—no, BootyConfigV1 has extra='forbid', so if data has {"security": {"enabled": true, "unknown": "x"}}, we'd pass that to BootyConfigV1 and the security field would receive {"enabled": true, "unknown": "x"}. SecurityConfig.model_validate would fail. So we need BootyConfigV1 to not validate security inline—we need a custom validator that catches and sets None. Or we parse security separately before passing to BootyConfigV1. Pre-parse: data_copy = dict(data); security_data = data_copy.pop("security", None); config = BootyConfigV1.model_validate(data_copy); if security_data: try config.security = SecurityConfig.model_validate(security_data); except: config.security = None. But that mutates after validate. Cleaner: have a validator on BootyConfigV1 that, for the security field, tries to parse and returns None on failure.

**How to avoid:** Use a field_validator for security that returns None when ValidationError occurs. Or parse security block in a separate step before BootyConfigV1.model_validate and pass validated security or None.

### Pitfall 2: Shared Queue with Verifier
**What goes wrong:** Reusing VerifierQueue for Security causes cross-agent dedup.
**Why:** Verifier and Security are independent; same PR should get both.
**How to avoid:** Separate SecurityQueue; separate security_queue in app.state.

### Pitfall 3: Security Runs Only on Agent PRs
**What goes wrong:** Scope creep—Security must run on every PR per ROADMAP.
**How to avoid:** No is_agent_pr check when enqueueing Security; enqueue for all opened/synchronize/reopened.

## Code Examples

### Verifier pull_request Enqueue (mirror for Security)
```python
# webhooks.py lines 161-217
action = payload.get("action")
if action not in ("opened", "synchronize", "reopened"):
    return {"status": "ignored"}
# ... extract owner, repo_name, pr_number, head_sha, installation_id ...
if security_queue.is_duplicate(pr_number, head_sha):
    return {"status": "already_processed"}  # or allow both Verifier and Security
job = SecurityJob(job_id=..., owner=..., repo_name=..., pr_number=..., head_sha=..., ...)
await security_queue.enqueue(job)
```

### create_check_run for booty/security
```python
# github/checks.py - add create_security_check_run
# Same as create_check_run but name="booty/security", output default title "Booty Security" or "Security"
kwargs = {
    "name": "booty/security",
    "head_sha": head_sha,
    "status": status,
    "output": output or {"title": "Booty Security", "summary": "Queued"},
}
return repo.create_check_run(**kwargs)
```

### SecurityConfig and BootyConfigV1
```python
class SecurityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    fail_severity: Literal["low", "medium", "high", "critical"] = "high"
    sensitive_paths: list[str] = Field(default_factory=lambda: [
        ".github/workflows/**", "infra/**", "terraform/**", "helm/**",
        "k8s/**", "iam/**", "auth/**", "security/**"
    ])

# BootyConfigV1
security: SecurityConfig | None = None  # optional
# Validator: if "security" in data, try parse; on fail set None
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Single agent per webhook | Multiple agents per event (Verifier + Security) | Shared pull_request; separate queues |
| PAT for checks | GitHub App | Same as Verifier |
| Config in env only | .booty.yml + env overrides | Governor pattern |

## Open Questions

1. **Cancel on new push:** CONTEXT says "Cancel in-progress, enqueue new run when synchronize with new SHA." Verifier doesn't explicitly cancel—new push sends new event with new head_sha, dedup avoids re-processing same sha, new sha gets enqueued. In-progress old job continues. For Phase 18, minimal scaffold may not need cancel—defer to later.
2. **Security uses same GitHub App as Verifier:** Yes—no extra app needed.

## Sources

### Primary (HIGH confidence)
- Existing codebase: webhooks.py, verifier/queue.py, verifier/runner.py, github/checks.py, test_runner/config.py
- Phase 14 plans: ReleaseGovernorConfig pattern

### Secondary
- GitHub Checks API docs: create_check_run, status=queued|in_progress|completed

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all existing
- Architecture: HIGH — mirror Verifier
- Pitfalls: HIGH — from codebase analysis

**Research date:** 2026-02-16
**Valid until:** 30 days
