# Project Research Summary

**Project:** Booty
**Domain:** Verifier agent — PR verification, Checks API, error-rate control
**Researched:** 2026-02-15
**Confidence:** HIGH

## Executive Summary

Adding a Verifier agent to Booty requires **GitHub App authentication** — the Checks API does not accept PATs. Booty currently uses `Auth.Token`; we must add an App auth path for Verifier. PyGithub supports both; no library swap. The Verifier runs on every PR (webhook: `pull_request` opened/synchronize), clones the PR head in a clean env, validates `.booty.yml`, enforces diff limits, detects import/compile failures, runs tests, and posts a check run `booty/verifier`. Reuse existing `test_runner` (executor, config); extend webhooks for `pull_request`.

**Key risk:** Assuming PAT works for Checks API — it does not. Phase 1 must deliver GitHub App auth before any check run logic.

## Key Findings

### Recommended Stack

- **GitHub App auth:** `Auth.AppAuth(app_id, private_key)` + `GithubIntegration.get_github_for_installation()`. Required for Checks API.
- **No new test runner:** Reuse `execute_tests()`, `load_booty_config()`.
- **Extend BootyConfig:** Add schema_version, allowed_paths, forbidden_paths for .booty.yml v1.
- **Dual auth:** Builder keeps PAT; Verifier uses App token for checks only.

### Expected Features

**Must have (table stakes):**
- Run tests in clean env (clone PR head, execute_tests)
- Block PR if red (Checks API conclusion: failure)
- Enforce diff limits (max_files_changed, max_diff_loc)
- Validate .booty.yml (schema_version: 1)
- Detect hallucinated imports / compile failures

**Should have:**
- max_loc_per_file for safety-critical dirs (pathspec-scoped)
- network_policy, allowed_commands in schema (defer to v1.2.1)

### Architecture Approach

- Extend webhook for `pull_request` (opened, synchronize)
- New `verifier/` module: job, runner, limits, imports
- New `booty/github/checks.py` for `create_check_run` (App auth)
- Reuse `prepare_workspace` pattern with variant: clone at `head_sha`

### Critical Pitfalls

1. **PAT for Checks API** — 403. Use GitHub App only.
2. **Wrong branch** — Clone PR head (`head_sha`), not base.
3. **Blocking human PRs** — Document branch protection; selective authority is via Builder promotion, merge gate is repo-level.
4. **.booty.yml breaking change** — schema_version with backward compat for v0.
5. **Race** — Use `head_sha` from webhook; it's authoritative.

## Implications for Roadmap

### Phase 7: GitHub App + Checks Integration

**Rationale:** Checks API blocks everything; must be first.
**Delivers:** Settings (APP_ID, PRIVATE_KEY), checks.py with create_check_run, manual test of check creation.
**Addresses:** VERIFY-01 (required check), FEATURES table stakes.
**Avoids:** PAT pitfall.

### Phase 8: pull_request Webhook + Verifier Runner

**Rationale:** Verifier needs PR events and orchestration.
**Delivers:** Webhook branch for pull_request; VerifierJob; process_pr_verification (clone, test, post check).
**Uses:** test_runner executor, checks module.
**Implements:** ARCHITECTURE runner.

### Phase 9: Diff Limits + .booty.yml Schema v1

**Rationale:** Blast-radius control and config validation.
**Delivers:** limits.py (max_files, max_loc); BootyConfig extension (schema_version, allowed_paths, forbidden_paths).
**Addresses:** Diff limits requirement.

### Phase 10: Import/Compile Detection

**Rationale:** Catch LLM hallucinations before test run.
**Delivers:** imports.py (AST validation); early failure from setup_command.
**Addresses:** Hallucinated imports, compile failures.

### Phase Ordering Rationale

- App auth first (unblocks Checks API)
- Webhook + runner second (core flow)
- Limits + schema third (validation layer)
- Import detection fourth (enhanced correctness)

### Research Flags

- **Phase 7:** Verify PyGithub `create_check_run` with App auth — may need `GithubIntegration.get_github_for_installation()` → `repo` → `create_check_run`. Confirm installation_id from webhook.
- **Phase 9:** pathspec for max_loc_per_file — need to map PR changed files to pathspec patterns for safety-critical dirs.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | GitHub docs + PyGithub Context7 verified |
| Features | HIGH | User requirements explicit |
| Architecture | HIGH | Existing codebase maps cleanly |
| Pitfalls | HIGH | Checks API auth well-documented |

**Overall confidence:** HIGH

### Gaps to Address

- **Installation ID:** Webhook payload includes `installation.id` for App installs. Confirm Booty receives it when App is installed on repo.
- **Branch protection:** "Required check" is user-configured. Document how to add booty/verifier.

## Sources

- PyGithub Context7 (CheckRun, Auth.AppAuth)
- GitHub REST API (Checks, authentication)
- Web search (Checks API requirements)
- Existing: webhooks.py, test_runner, config.py

---
*Research completed: 2026-02-15*
*Ready for roadmap: yes*
