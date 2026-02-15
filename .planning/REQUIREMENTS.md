# Requirements: Booty v1.1

**Defined:** 2026-02-15
**Core Value:** A Builder agent that can take a GitHub issue and produce a working PR with tested code — the foundation everything else builds on.

## v1.1 Requirements

### Test Generation

- [ ] **TGEN-01**: Builder generates unit tests for all changed files in every PR
- [ ] **TGEN-02**: Generated tests use correct framework (pytest) and project conventions
- [ ] **TGEN-03**: Generated tests are placed in correct directory with correct naming
- [ ] **TGEN-04**: Generated test dependencies are verified (no hallucinated imports)
- [ ] **TGEN-05**: Generated tests pass before PR is finalized

### PR Promotion

- [ ] **PRMO-01**: Draft PR is promoted to ready-for-review when all tests pass
- [ ] **PRMO-02**: Promotion fails gracefully (leave as draft, log error) if API call fails
- [ ] **PRMO-03**: Multi-criteria validation before promotion (tests pass + linting clean)

## Future Requirements

### Test Backfill

- **TBKF-01**: Builder generates tests for existing v1.0 code retroactively
- **TBKF-02**: Integration tests for cross-component workflows

## Out of Scope

| Feature | Reason |
|---------|--------|
| 100% coverage targeting | Over-constrains LLM, diminishing returns |
| Separate test-only LLM call | Context lost, duplicates work — generate tests alongside code |
| Auto-merge PRs | Too dangerous, erodes trust |
| Coverage reporting integration | Nice-to-have, not core to test generation |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TGEN-01 | Phase 5 | Pending |
| TGEN-02 | Phase 5 | Pending |
| TGEN-03 | Phase 5 | Pending |
| TGEN-04 | Phase 5 | Pending |
| TGEN-05 | Phase 5 | Pending |
| PRMO-01 | Phase 6 | Pending |
| PRMO-02 | Phase 6 | Pending |
| PRMO-03 | Phase 6 | Pending |

**Coverage:**
- v1.1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-15*
*Last updated: 2026-02-15 after roadmap creation*
