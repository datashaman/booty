# Project Milestones: Booty

## v1.2 Verifier Agent (Shipped: 2026-02-15)

**Delivered:** Verifier agent runs on every PR, runs tests in clean env, enforces diff limits, validates .booty.yml, detects import/compile failures, posts check run `booty/verifier`.

**Phases completed:** 7-10 (12 plans total)

**Key accomplishments:**

- GitHub App + Checks API integration (create_check_run, edit_check_run) with booty status and booty verifier check-test CLI
- Verifier runner with VerifierJob, prepare_verification_workspace, process_verifier_job — check lifecycle queued → in_progress → completed
- pull_request webhook, VerifierQueue with dedup, agent:builder label, Builder never promotes — Verifier owns promotion and failure comments
- BootyConfigV1 schema with load_booty_config_from_content; verifier/limits.py (max_files_changed, max_diff_loc, max_loc_per_file)
- verifier/imports.py: compile_sweep, validate_imports; full pipeline setup → install → import/compile → tests
- 12/12 v1.2 requirements satisfied; milestone audit passed

**Stats:**

- 68 files modified (v1.1..v1.2)
- 5,615 lines of Python (total)
- 4 phases, 12 plans
- 1 day from v1.1 to ship (2026-02-15)

**Git range:** `0238b69` (docs: start milestone v1.2) → `aaca2ee` (Merge PR #9)

**What's next:** TBD — run `/gsd:new-milestone` to define

---

## v1.1 Test Generation & PR Promotion (Shipped: 2026-02-15)

**Delivered:** Builder generates unit tests for all changed files and promotes draft PRs to ready-for-review when tests and linting pass.

**Phases completed:** 5-6 (4 plans total)

**Key accomplishments:**

- Convention detection module with language-agnostic test conventions and AST-based import validation
- LLM integration for single-call code+test generation using detected conventions
- Promotion module with GraphQL promote_to_ready_for_review and tenacity retry (5xx/network only)
- Pipeline wiring: quality checks for all jobs, draft PRs promoted when tests+lint pass (self-mod excluded)
- 8/8 v1.1 requirements satisfied

**Stats:**

- 41 files modified (v1.0..v1.1)
- ~5,000 net LOC added (4,052 total Python)
- 2 phases, 4 plans
- 1 day from v1.0 to ship (2026-02-14 → 2026-02-15)

**Git range:** `efac606` (docs: start milestone v1.1) → `3e2e17c` (docs(05): add Phase 5 verification)

**What's next:** TBD — run `/gsd:new-milestone` to define

---

## v1.0 MVP (Shipped: 2026-02-14)

**Delivered:** A Builder agent that picks up GitHub issues, writes code via LLM, runs tests with iterative refinement, and opens PRs — including against its own repository.

**Phases completed:** 1-4 (13 plans total)

**Key accomplishments:**

- FastAPI webhook receiver with HMAC-SHA256 verification and async job queue with worker pool
- End-to-end LLM code generation pipeline transforming GitHub issues into pull requests in 12 steps
- Iterative test-driven refinement with failure feedback loops and exponential backoff
- Self-modification capability with protected path enforcement, quality gates (ruff), and draft PR safety
- 17/17 v1 requirements satisfied with 100% milestone audit pass

**Stats:**

- 77 files created/modified
- 3,012 lines of Python
- 4 phases, 13 plans
- 1 day from init to ship (2026-02-14)

**Git range:** `6d6b356` (docs: initialize project) → `9a70cae` (docs(04): complete self-modification phase)

**What's next:** v1.1 — TBD (run `/gsd:new-milestone` to define)

---
