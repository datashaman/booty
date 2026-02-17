# Requirements: Booty v1.9 Reviewer Agent

**Defined:** 2026-02-17
**Core Value:** A Builder agent that can take a GitHub issue and produce a working PR with tested code — the foundation everything else builds on.

## v1.9 Requirements

Requirements for Reviewer Agent milestone. Each maps to roadmap phases.

### Triggering and Scope

- [ ] **REV-01**: Reviewer runs on pull_request opened and synchronize (optionally reopened to match Verifier)
- [ ] **REV-02**: Reviewer runs only for agent PRs (same detection rule as elsewhere)
- [ ] **REV-03**: Dedup key (repo, pr_number, head_sha); new synchronize with new SHA cancels prior in-progress review (best-effort)

### Check Run Lifecycle

- [ ] **REV-04**: Required check `booty/reviewer` with states queued → in_progress → success|failure
- [ ] **REV-05**: Check titles: Queued/In progress "Booty Reviewer"; Success "Reviewer approved" or "Reviewer approved with suggestions"; Failure "Reviewer blocked"

### Decisions

- [ ] **REV-06**: APPROVED → check success, no comment required
- [ ] **REV-07**: APPROVED_WITH_SUGGESTIONS → check success + comment with suggestions
- [ ] **REV-08**: BLOCKED → check failure + comment with reasons and guidance; blocks promotion
- [x] **REV-09**: Fail-open: infra/LLM/tooling failure yields check success with "Reviewer unavailable (fail-open)"; increments reviewer_fail_open

### PR Comment

- [ ] **REV-10**: Single updatable PR comment with marker `<!-- booty-reviewer -->`; outcome, findings by category, suggested fixes with file/path references

### Evaluation Criteria

- [ ] **REV-11**: Reviewer evaluates: maintainability, overengineering, duplication, test quality, naming/API, architectural regression (no style/formatting)

### Configuration

- [ ] **REV-12**: `.booty.yml` reviewer block: enabled, block_on (overengineering, poor_tests, duplication, architectural_regression); missing block => disabled by default
- [ ] **REV-13**: Unknown reviewer keys fail Reviewer only; env override REVIEWER_ENABLED wins over file

### Promotion Gate

- [ ] **REV-14**: Builder promotion requires booty/reviewer success AND booty/verifier success for agent PRs; fail-open success still counts

### Metrics

- [x] **REV-15**: Emit reviews_total, reviews_blocked, reviews_suggestions, reviewer_fail_open; structured logs with repo, pr, sha, outcome, blocked_categories, suggestion_count

## Future Requirements

Deferred to later milestones.

### CLI

- **REV-16**: `booty reviewer review --pr N` (optional future)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Re-running tests/lint/security | Verifier, Security already cover |
| Formatting/style nitpicks | Reviewer focuses on quality, not style |
| Dependency scanning | Security Agent covers |
| Merge policy | Reviewer only affects promotion; Verifier is merge gate |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REV-04 | 37 | Complete |
| REV-10 | 37 | Complete |
| REV-12 | 37 | Complete |
| REV-13 | 37 | Complete |
| REV-01 | 38 | Complete |
| REV-02 | 38 | Complete |
| REV-03 | 38 | Complete |
| REV-05 | 38 | Complete |
| REV-06 | 39 | Complete |
| REV-07 | 39 | Complete |
| REV-08 | 39 | Complete |
| REV-11 | 39 | Complete |
| REV-14 | 40 | Complete |
| REV-09 | 41 | Complete |
| REV-15 | 41 | Complete |

**Coverage:**
- v1.9 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-17*
*Last updated: 2026-02-17 after v1.9 milestone definition*
