# Phase 40: Promotion Gating - Research

**Researched:** 2026-02-17
**Domain:** GitHub Checks API, Verifier promotion flow, Reviewer config
**Confidence:** HIGH

## Summary

Phase 40 gates promotion of agent PRs on both booty/reviewer and booty/verifier success. Verifier currently promotes on tests_passed; we add a check: when Reviewer is enabled, require booty/reviewer check conclusion=success before promoting. Fail-open success (Phase 41) will post conclusion=success, so no special handling needed now.

The implementation is internal: extend Verifier runner, add a helper to fetch booty/reviewer check status for a commit, use existing Reviewer config (get_reviewer_config, apply_reviewer_env_overrides). No new libraries. PyGithub Repository.get_check_runs supports listing checks by head_sha and check_name.

**Primary recommendation:** Add reviewer_check_success helper in checks.py or verifier; before promote in runner.py, if reviewer enabled require booty/reviewer success.

## Standard Stack

No new dependencies. Use existing:

| Component | Purpose |
|-----------|---------|
| PyGithub Repository.get_check_runs | List check runs for commit; filter by check_name |
| get_reviewer_config + apply_reviewer_env_overrides | Reviewer enabled state from .booty.yml |
| get_verifier_repo | GitHub App auth for Checks API read |

## Architecture Patterns

### Check Run Status Query

PyGithub: `repo.get_check_runs(head_sha=sha, check_name="booty/reviewer")` returns PaginatedList of CheckRun. Each has:
- `status`: "queued" | "in_progress" | "completed"
- `conclusion`: "success" | "failure" | "neutral" | "cancelled" | "skipped" | None (when status != completed)

**Success =** status=="completed" and conclusion=="success". Fail-open (Phase 41) will post success, so conclusion=="success" covers it.

### Reviewer-Enabled Detection

Verifier already loads .booty.yml for agent PRs before clone (load_booty_config_from_content). Config may be BootyConfig (v0, no reviewer) or BootyConfigV1 (reviewer: dict | None). Use:

```python
from booty.reviewer.config import get_reviewer_config, apply_reviewer_env_overrides
rc = get_reviewer_config(config)  # returns ReviewerConfig | None
if rc:
    rc = apply_reviewer_env_overrides(rc)
    reviewer_enabled = rc.enabled
```

### Promotion Flow (Current → Phase 40)

1. Verifier completes tests, updates booty/verifier check.
2. If agent PR and tests_passed:
   - If reviewer enabled: fetch booty/reviewer for head_sha; if completed and conclusion==success → promote; else exit with check success, leave PR draft.
   - If reviewer disabled: promote (current behavior).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Fetch check runs | Raw REST call | repo.get_check_runs(head_sha=..., check_name="booty/reviewer") |
| Reviewer config | Custom parser | get_reviewer_config, apply_reviewer_env_overrides |

## Common Pitfalls

### Pitfall: Race with Reviewer

**What:** Verifier may complete before Reviewer (or Reviewer not yet triggered).  
**Why:** Reviewer runs on pull_request; Verifier runs on check_suite or pull_request. Order can vary.  
**How to avoid:** If reviewer enabled and booty/reviewer not found or not completed → do NOT promote. Exit with success; PR stays draft. Reviewer will run; when it completes, neither Verifier nor Reviewer currently re-checks. CONTEXT says "green-waiting acceptable" — the second check completing will observe the other. Verifier is often second (tests take longer); if Verifier completes first and Reviewer not done, we don't promote. If Reviewer completes first and Verifier not done, Verifier will later promote when it completes (and we'll see Reviewer success). So: Verifier only promotes when BOTH passed at promote-time.

### Pitfall: Config Parsing Errors

**What:** get_reviewer_config raises ReviewerConfigError on unknown keys.  
**How to avoid:** Verifier already catches ValidationError for config. If get_reviewer_config raises, treat as reviewer disabled (fail closed on config error is acceptable per decisions).

## Code Examples

### Check Reviewer Success

```python
def reviewer_check_success(repo, head_sha: str) -> bool:
    """True if booty/reviewer check exists, is completed, and conclusion is success."""
    try:
        runs = repo.get_check_runs(head_sha=head_sha, check_name="booty/reviewer")
        for run in runs:
            if run.status == "completed" and run.conclusion == "success":
                return True
        return False
    except Exception:
        return False
```

### Is Reviewer Enabled (from pre-clone config)

```python
from booty.reviewer.config import get_reviewer_config, apply_reviewer_env_overrides
rc = get_reviewer_config(config)  # config from load_booty_config_from_content
if rc is None:
    reviewer_enabled = False
else:
    rc = apply_reviewer_env_overrides(rc)
    reviewer_enabled = rc.enabled
```

## Sources

### Primary (HIGH confidence)
- PyGithub Repository — get_check_runs(head_sha, check_name)
- booty.reviewer.config — get_reviewer_config, apply_reviewer_env_overrides
- src/booty/verifier/runner.py — current promotion logic
- 40-CONTEXT.md — decisions (Verifier gates; no promote until both success)

---

*Phase: 40-promotion-gating*
*Research date: 2026-02-17*
