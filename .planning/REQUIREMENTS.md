# Requirements: Booty v1.2 Verifier Agent

**Defined:** 2026-02-15
**Core Value:** A Builder agent that can take a GitHub issue and produce a working PR with tested code — Verifier controls error rate so capability doesn't outpace correctness.

## v1.2 Requirements

Requirements for Verifier agent milestone. Each maps to roadmap phases.

### Verification Pipeline

- [x] **VERIFY-01**: Verifier posts required status check `booty/verifier` via GitHub Checks API (GitHub App auth)
- [ ] **VERIFY-02**: Verifier runs on every PR (webhook: pull_request opened, synchronize); enforces gates only for agent PRs (agent:builder label or bot author)
- [ ] **VERIFY-03**: Verifier clones PR head in clean env and runs tests via execute_tests()
- [ ] **VERIFY-04**: Verifier blocks PR if red — promotion control (Builder skips promote) and Checks API conclusion: failure
- [ ] **VERIFY-05**: Verifier optionally comments diagnostics on PR (universal visibility)

### Diff Limits

- [ ] **VERIFY-06**: Verifier enforces max_files_changed (from .booty.yml or default)
- [ ] **VERIFY-07**: Verifier enforces max_diff_loc (added + deleted lines)
- [ ] **VERIFY-08**: Verifier enforces max_loc_per_file for safety-critical dirs (optional, pathspec-scoped)

### Configuration

- [ ] **VERIFY-09**: Verifier validates .booty.yml against schema_version: 1 before running
- [ ] **VERIFY-10**: .booty.yml schema v1 supports: test_command, setup_command?, timeout_seconds, max_retries, allowed_paths, forbidden_paths, allowed_commands, network_policy, labels

### Correctness Detection

- [ ] **VERIFY-11**: Verifier detects hallucinated imports (AST validation; imports must resolve)
- [ ] **VERIFY-12**: Verifier detects compile failures (setup_command / early test failure capture)

## Future Requirements

Deferred to later milestones.

### v1.2.x

- **VERIFY-13**: network_policy, allowed_commands enforcement in Verifier (schema exists, enforcement deferred)
- **VERIFY-14**: Aggregate CI check results (Verifier consumes existing CI; defer)

### v1.3+

- Builder generates integration tests

## Out of Scope

| Feature | Reason |
|---------|--------|
| Rely on CI only (no Verifier) | CI reports; Verifier decides — separation of concerns |
| Block human PRs differently via GitHub | Branch protection is repo-level; document setup |
| Custom LLM for verification | Static analysis + test run; no LLM in Verifier |

## Traceability

Which phases cover which requirements.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VERIFY-01 | Phase 7 | Complete |
| VERIFY-02 | Phase 8 | Pending |
| VERIFY-03 | Phase 8 | Pending |
| VERIFY-04 | Phase 8 | Pending |
| VERIFY-05 | Phase 8 | Pending |
| VERIFY-06 | Phase 9 | Pending |
| VERIFY-07 | Phase 9 | Pending |
| VERIFY-08 | Phase 9 | Pending |
| VERIFY-09 | Phase 9 | Pending |
| VERIFY-10 | Phase 9 | Pending |
| VERIFY-11 | Phase 10 | Pending |
| VERIFY-12 | Phase 10 | Pending |

**Coverage:**
- v1.2 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-15*
*Last updated: 2026-02-15 after research*
