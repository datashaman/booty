# Roadmap: Booty

## Milestones

- ✅ **v1.0 MVP** - Phases 1-4 (shipped 2026-02-14)
- 🚧 **v1.1 Test Generation & PR Promotion** - Phases 5-6 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) - SHIPPED 2026-02-14</summary>

Delivered a Builder agent that picks up GitHub issues, writes code via LLM, runs tests with iterative refinement, and opens PRs — including against its own repository.

**Stats:** 77 files, 3,012 LOC Python, 4 phases, 13 plans, 1 day execution

See MILESTONES.md for details.

</details>

### 🚧 v1.1 Test Generation & PR Promotion (In Progress)

**Milestone Goal:** Make the Builder generate tests with every code change and promote PRs to ready-for-review only when tests pass.

#### Phase 5: Test Generation

**Goal**: Builder generates and validates unit tests for all code changes

**Depends on**: Phase 4 (v1.0 baseline)

**Requirements**: TGEN-01, TGEN-02, TGEN-03, TGEN-04, TGEN-05

**Success Criteria** (what must be TRUE):
  1. Builder generates unit test files for all changed source files in every PR
  2. Generated tests use pytest framework and follow project naming conventions (tests/test_*.py)
  3. Generated tests are placed in correct directory structure matching source layout
  4. Generated test imports are verified against installed packages before execution (no hallucinated dependencies)
  5. All generated tests pass before PR is finalized

**Plans:** 2 plans

Plans:
- [x] 05-01-PLAN.md — Convention detection and import validation module
- [x] 05-02-PLAN.md — LLM integration and pipeline wiring

#### Phase 6: PR Promotion

**Goal**: Draft PRs are automatically promoted to ready-for-review when validation passes

**Depends on**: Phase 5 (needs working test generation)

**Requirements**: PRMO-01, PRMO-02, PRMO-03

**Success Criteria** (what must be TRUE):
  1. Draft PR is promoted to ready-for-review state when all tests pass and linting is clean
  2. Promotion failures (network errors, API issues) are logged gracefully without failing the entire job
  3. Multi-criteria validation is performed before promotion (tests + linting + not self-modification)
  4. Self-modification PRs always remain as draft requiring manual review

**Plans**: TBD

Plans:
- [ ] TBD (determined during `/gsd:plan-phase 6`)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | Complete | 2026-02-14 |
| 2. GitHub Integration | v1.0 | 3/3 | Complete | 2026-02-14 |
| 3. Test-Driven Refinement | v1.0 | 4/4 | Complete | 2026-02-14 |
| 4. Self-Modification Safety | v1.0 | 3/3 | Complete | 2026-02-14 |
| 5. Test Generation | v1.1 | 2/2 | Complete | 2026-02-15 |
| 6. PR Promotion | v1.1 | 0/TBD | Not started | - |

---
*Last updated: 2026-02-15 after Phase 5 completion*
