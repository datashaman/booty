# Requirements: Booty v1.8 Architect Agent

**Defined:** 2026-02-17
**Core Value:** A Builder agent that can take a GitHub issue and produce a working PR with tested code.

## v1.8 Requirements

Requirements for Architect Agent milestone. Each maps to roadmap phases.

### Position & Triggering

- [ ] **ARCH-01**: Architect runs only after Planner successfully generates a plan (subscribes to Planner completion, not GitHub labels)
- [ ] **ARCH-02**: Architect triggers when Planner posts/updates plan comment (issues.opened agent:plan, issues.labeled agent:plan, booty plan CLI)
- [ ] **ARCH-03**: Architect never runs directly from GitHub labels; only from Planner completion event

### Inputs

- [ ] **ARCH-04**: Architect receives plan_json, normalized_input, optional repo_context, optional issue_metadata
- [ ] **ARCH-05**: Architect must operate when repo_context is missing

### Validation — Structural Integrity

- [ ] **ARCH-06**: Architect validates steps ≤ 12
- [ ] **ARCH-07**: Architect validates each step has id + action
- [ ] **ARCH-08**: Architect validates actions ∈ {read, add, edit, run, verify, research}

### Validation — Path Consistency

- [ ] **ARCH-09**: Architect validates touch_paths == union(step.paths)
- [ ] **ARCH-10**: Architect flags empty paths unless justified

### Validation — Risk Accuracy

- [ ] **ARCH-11**: Architect recomputes risk from touch_paths (HIGH: .github/workflows/, infra/, migrations, lockfiles; MEDIUM: manifests; else LOW)
- [ ] **ARCH-12**: Architect overrides Planner risk when it differs from recomputed value

### Validation — Ambiguity & Overreach

- [ ] **ARCH-13**: Architect rewrites steps when instructions are vague (configurable: rewrite_ambiguous_steps)
- [ ] **ARCH-14**: Architect detects overreach (repo-wide refactors, multi-domain rewrites, speculative arch changes)
- [ ] **ARCH-15**: Architect rewrites into smaller scope when possible

### Output

- [ ] **ARCH-16**: Architect produces ArchitectPlan (plan_version, goal, steps, touch_paths, risk_level, handoff_to_builder, architect_notes)
- [ ] **ARCH-17**: architect_notes is optional and not consumed by Builder
- [ ] **ARCH-18**: Architect updates existing plan comment with <!-- booty-architect --> section (Approved or Rewritten)

### Failure Handling

- [ ] **ARCH-19**: When plan cannot be safely rewritten, Architect posts "Architect review required — plan is structurally unsafe."
- [ ] **ARCH-20**: Architect applies agent:architect-review label on block
- [ ] **ARCH-21**: Architect does NOT trigger Builder when blocked
- [ ] **ARCH-22**: No automatic retries on block

### Idempotency

- [ ] **ARCH-23**: Architect hashes plan_hash = sha256(plan_json)
- [ ] **ARCH-24**: Same plan approved within 24h reuses ArchitectPlan, no rewrite
- [ ] **ARCH-25**: Architect updates comment only if changed on cache hit

### Builder Handoff

- [ ] **ARCH-26**: Architect persists approved artifact to ~/.booty/state/plans/<repo>/<issue>-architect.json
- [ ] **ARCH-27**: Architect emits planner.plan.approved (internal event) when approved
- [ ] **ARCH-28**: Builder listens for planner.plan.approved (or equivalent handoff) — Builder no longer triggers from agent:builder

### CLI

- [ ] **ARCH-29**: booty architect status shows enabled, plans reviewed (24h), rewrites count
- [ ] **ARCH-30**: booty architect review --issue N forces re-evaluation

### Configuration

- [ ] **ARCH-31**: .booty.yml architect block (enabled, rewrite_ambiguous_steps, enforce_risk_rules)
- [ ] **ARCH-32**: enabled defaults to true; unknown keys fail Architect only

### Observability

- [ ] **ARCH-33**: Architect emits metrics: plans_reviewed, plans_rewritten, architect_blocks, cache_hits

### Performance

- [ ] **ARCH-34**: Architect target runtime < 5 seconds

## Future Requirements (v1.x+)

Deferred to later milestones.

- Architect LLM-assisted rewrite for complex ambiguity — v1.8 uses rule-driven rewrites only

## Out of Scope

| Feature | Reason |
|---------|--------|
| Architect generates code | Architect rewrites plan only; Builder executes |
| Architect runs tests | Builder/Verifier own execution |
| Architect modifies repositories | Planning authority only |
| Architect deploys | Governor owns deploy |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ARCH-01 | 32 | Complete |
| ARCH-02 | 32 | Complete |
| ARCH-03 | 32 | Complete |
| ARCH-04 | 32 | Complete |
| ARCH-05 | 32 | Complete |
| ARCH-06 | 33 | Complete |
| ARCH-07 | 33 | Complete |
| ARCH-08 | 33 | Complete |
| ARCH-09 | 33 | Complete |
| ARCH-10 | 33 | Complete |
| ARCH-11 | 33 | Complete |
| ARCH-12 | 33 | Complete |
| ARCH-13 | 33 | Complete |
| ARCH-14 | 33 | Complete |
| ARCH-15 | 33 | Complete |
| ARCH-16 | 34 | Pending |
| ARCH-17 | 34 | Pending |
| ARCH-18 | 34 | Pending |
| ARCH-19 | 34 | Pending |
| ARCH-20 | 34 | Pending |
| ARCH-21 | 34 | Pending |
| ARCH-22 | 34 | Pending |
| ARCH-23 | 35 | Pending |
| ARCH-24 | 35 | Pending |
| ARCH-25 | 35 | Pending |
| ARCH-26 | 36 | Pending |
| ARCH-27 | 36 | Pending |
| ARCH-28 | 36 | Pending |
| ARCH-29 | 36 | Pending |
| ARCH-30 | 36 | Pending |
| ARCH-31 | 32 | Complete |
| ARCH-32 | 32 | Complete |
| ARCH-33 | 36 | Pending |
| ARCH-34 | 33 | Complete |

**Coverage:**
- v1.8 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-17*
*Last updated: 2026-02-17 after initial definition*
