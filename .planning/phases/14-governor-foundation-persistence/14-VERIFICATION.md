# Phase 14 Verification

**Phase:** 14-governor-foundation-persistence
**Goal:** Config schema, release state store, agent skeleton, deploy workflow sha input.
**Status:** passed
**Date:** 2026-02-16

## Must-Haves Verified

### Success criteria 1: ReleaseGovernorConfig schema
- ✓ ReleaseGovernorConfig in src/booty/test_runner/config.py with extra="forbid"
- ✓ apply_release_governor_env_overrides for RELEASE_GOVERNOR_* env vars
- ✓ BootyConfigV1.release_governor optional field

### Success criteria 2: release.json state store
- ✓ src/booty/release_governor/store.py: ReleaseState, load_release_state, save_release_state
- ✓ Atomic write via temp + os.replace
- ✓ fcntl.flock for single-writer safety
- ✓ get_state_dir creates .booty/state when used

### Success criteria 3: Delivery ID cache
- ✓ has_delivery_id, record_delivery_id in store.py
- ✓ Keyed by "repo:sha" for (repo, head_sha) dedup

### Success criteria 4: release_governor module
- ✓ src/booty/release_governor/: __init__.py, store.py, handler.py
- ✓ Config + store as specified

### Success criteria 5: Deploy workflow sha input
- ✓ .github/workflows/deploy.yml: workflow_dispatch inputs.sha
- ✓ Preflight fails when workflow_dispatch without sha
- ✓ Checkout ref: inputs.sha || github.sha
- ✓ DEPLOY_SHA passed to deploy step
- ✓ deploy.sh: git fetch + checkout when DEPLOY_SHA set

### Success criteria 6: Verify-main workflow
- ✓ .github/workflows/verify-main.yml on push to main
- ✓ booty verifier run executes tests from .booty.yml
- ✓ Reuses execute_tests from test_runner

## Gaps

None.
