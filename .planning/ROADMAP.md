# Roadmap: Booty

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-02-14)
- ✅ **v1.1 Test Generation & PR Promotion** — Phases 5-6 (shipped 2026-02-15)
- ✅ **v1.2 Verifier Agent** — Phases 7-10 (shipped 2026-02-15)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-02-14</summary>

Delivered a Builder agent that picks up GitHub issues, writes code via LLM, runs tests with iterative refinement, and opens PRs — including against its own repository.

**Stats:** 77 files, 3,012 LOC Python, 4 phases, 13 plans, 1 day execution

See [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) and [MILESTONES.md](MILESTONES.md) for details.

</details>

<details>
<summary>✅ v1.1 Test Generation & PR Promotion (Phases 5-6) — SHIPPED 2026-02-15</summary>

Builder generates unit tests for all changed files and promotes draft PRs to ready-for-review when tests and linting pass.

**Stats:** 4 plans, 2 phases, 41 files modified (v1.0..v1.1)

See [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md) and [MILESTONES.md](MILESTONES.md) for details.

</details>

<details>
<summary>✅ v1.2 Verifier Agent (Phases 7-10) — SHIPPED 2026-02-15</summary>

Verifier agent runs on every PR, runs tests in clean env, enforces diff limits, validates .booty.yml, detects import/compile failures, posts check run `booty/verifier`.

**Requirements:** VERIFY-01 through VERIFY-12 (all complete)

</details>

---

## Phase 7: GitHub App + Checks Integration

**Goal:** Unblock Checks API — create `booty/verifier` check run using GitHub App auth.

**Requirements:** VERIFY-01

**Plans:** 3 plans

Plans:
- [x] 07-01-PLAN.md — Settings extension, verifier enabled check, startup log
- [x] 07-02-PLAN.md — checks.py with create_check_run (App auth)
- [x] 07-03-PLAN.md — CLI (booty status, booty verifier check-test), docs

**Success criteria:**
1. Settings include GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY (optional when empty — Verifier disabled)
2. `booty/github/checks.py` creates check run via `repo.create_check_run()` with App token
3. Manual test: create check run on a commit returns 201, check visible in GitHub UI

**Deliverables:** checks.py, Settings extension, GitHub App setup docs

---

## Phase 8: pull_request Webhook + Verifier Runner

**Goal:** Verifier runs on every PR, clones head, runs tests, posts check result.

**Requirements:** VERIFY-02, VERIFY-03, VERIFY-04, VERIFY-05

**Plans:** 3 plans

Plans:
- [x] 08-01-PLAN.md — Verifier runner (VerifierJob, workspace, process_verifier_job)
- [x] 08-02-PLAN.md — pull_request webhook branch, VerifierQueue, workers
- [x] 08-03-PLAN.md — Builder skip promote, agent:builder label, Verifier promotion/comment

**Success criteria:**
1. Webhook accepts `pull_request` (opened, synchronize); enqueues VerifierJob
2. Verifier clones PR head_sha in clean env, loads .booty.yml, runs execute_tests()
3. Check run transitions: queued → in_progress → completed (success/failure)
4. Agent PRs: Builder skips promotion when Verifier fails
5. Optional: PR comment with diagnostics when check fails

**Deliverables:** webhooks.py extension, verifier/ (job, runner), checks integration

---

## Phase 9: Diff Limits + .booty.yml Schema v1

**Goal:** Enforce diff limits and validate extended .booty.yml schema.

**Requirements:** VERIFY-06, VERIFY-07, VERIFY-08, VERIFY-09, VERIFY-10

**Plans:** 3 plans

Plans:
- [x] 09-01-PLAN.md — BootyConfig schema v1, load_booty_config_from_content
- [x] 09-02-PLAN.md — verifier/limits.py (DiffStats, check_diff_limits)
- [x] 09-03-PLAN.md — Wire schema + limits into runner

**Success criteria:**
1. Verifier rejects PR exceeding max_files_changed or max_diff_loc (check failure)
2. Optional max_loc_per_file enforced for pathspec-matched safety-critical dirs
3. .booty.yml with schema_version: 1 validated; unknown/malformed config fails check
4. Schema supports: test_command, setup_command?, timeout_seconds, max_retries, allowed_paths, forbidden_paths, allowed_commands, network_policy, labels
5. Backward compat: repos without schema_version use v0 (existing BootyConfig)

**Deliverables:** verifier/limits.py, BootyConfig extension, schema docs

---

## Phase 10: Import/Compile Detection

**Goal:** Detect hallucinated imports and compile failures before/during test run.

**Requirements:** VERIFY-11, VERIFY-12

**Plans:** 3 plans

Plans:
- [x] 10-01-PLAN.md — install_command schema, BootyConfigV1
- [x] 10-02-PLAN.md — verifier/imports.py (compile sweep, import validation)
- [x] 10-03-PLAN.md — Wire runner: execution order, annotations

**Success criteria:**
1. Verifier parses changed files (AST); validates imports resolve to existing modules
2. Unresolvable import → check failure with clear message
3. setup_command or test run compile failure (e.g. SyntaxError) → check failure
4. Failures reported in check output (title, summary, annotations where applicable)

**Deliverables:** verifier/imports.py, early-failure capture in runner

---

## Progress

| Phase | Milestone | Goal | Status |
|-------|-----------|------|--------|
| 1. Foundation | v1.0 | Webhook, clone, job queue | Complete |
| 2. GitHub Integration | v1.0 | LLM, PR creation | Complete |
| 3. Test-Driven Refinement | v1.0 | Tests, refinement loop | Complete |
| 4. Self-Modification Safety | v1.0 | Protected paths, draft PR | Complete |
| 5. Test Generation | v1.1 | Unit tests for changed files | Complete |
| 6. PR Promotion | v1.1 | Draft → ready when green | Complete |
| 7. GitHub App + Checks | v1.2 | Checks API integration | Complete |
| 8. Verifier Runner | v1.2 | PR webhook, clone, test, check | Complete |
| 9. Diff Limits + Schema | v1.2 | Limits, .booty.yml v1 | Complete |
| 10. Import/Compile Detection | v1.2 | Hallucination detection | Complete |

---
*Last updated: 2026-02-15 — v1.2 roadmap created*
