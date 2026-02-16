# Phase 21: Permission Drift & Governor Integration — Verification

**Status:** passed
**Date:** 2026-02-16

## Phase Goal

Sensitive paths → ESCALATE; persist override; Governor consumes.

## Must-Haves Verification

### 1. Sensitive paths matched (default patterns)

**Verified:** ✓

- `src/booty/test_runner/config.py` SecurityConfig.sensitive_paths default: `.github/workflows/**`, `infra/**`, `terraform/**`, `helm/**`, `k8s/**`, `iam/**`, `auth/**`, `security/**`
- `permission_drift.sensitive_paths_touched` uses PathSpec gitwildmatch
- Config can override via .booty.yml security.sensitive_paths

### 2. Touched → ESCALATE (not FAIL); title "Security escalated — workflow modified"

**Verified:** ✓

- `runner.py` lines 251–265: when `touched` → `edit_check_run(conclusion="success", output={"title": title, ...})`
- Title from `_title_for_paths`: "Security escalated — workflow modified" for `.github/workflows/`, "Security escalated — infra modified" for `infra/`, etc.
- Conclusion is `success` (merge allowed), not `failure`

### 3. Override persisted: risk_override=HIGH, reason=permission_surface_change, sha

**Verified:** ✓

- `override.py` persist_override: `{"risk_override": "HIGH", "reason": "permission_surface_change", "sha": sha, "paths": paths, "created_at": ...}`
- Stored in `state_dir/security_overrides.json`
- Key: `{repo_full_name}:{sha}`

### 4. Governor reads override for head_sha before compute_decision; uses HIGH when present

**Verified:** ✓

- `handler.py`: `override = get_security_override_with_poll(state_dir, repo_full_name, head_sha)`
- If override not None: `risk_class = "HIGH"`
- Else: `risk_class = compute_risk_class(comparison, config)`
- Same pattern in both `handle_workflow_run` and `simulate_decision_for_cli`

### 5. PR is not blocked — only deploy risk escalated

**Verified:** ✓

- ESCALATE uses `conclusion="success"` — check passes
- PR can merge; Governor uses HIGH for deploy gating when override present

### Renames checked

**Verified:** ✓

- `permission_drift.get_changed_paths` returns `(path, old_path)` for renames (git diff --find-renames)
- `sensitive_paths_touched` matches both path and old_path against PathSpec

## Test Coverage

- `test_security_permission_drift.py`: sensitive_paths_touched, _title_for_paths, get_changed_paths
- `test_security_override.py`: persist_override schema, merge
- `test_release_governor_override.py`: get_security_override, prune, poll, handler HIGH when override present

## Gaps

None.

## Human Verification

None required.
