# Requirements: Booty v1.7 Planner Agent

**Defined:** 2026-02-16
**Core Value:** A Builder agent that can take a GitHub issue and produce a working PR with tested code.

## v1.7 Requirements

Requirements for Planner Agent milestone. Each maps to roadmap phases.

### Inputs

- [ ] **PLAN-01**: Planner accepts GitHub Issue payload (title, body, labels)
- [ ] **PLAN-02**: Planner accepts Observability incident issue format
- [ ] **PLAN-03**: Planner accepts operator CLI prompt (free text) via `booty plan --text "..."`
- [ ] **PLAN-04**: Planner can use optional repo context (default branch, tree, recent commits) when available

### Plan Output

- [ ] **PLAN-05**: Planner produces structured Plan JSON conforming to schema (plan_version, goal, assumptions, constraints, risk_level, touch_paths, steps, tests, rollback, handoff_to_builder)
- [ ] **PLAN-06**: Plan has max 12 steps; each step has id (P1..Pn), action (read|edit|add|run|verify), path, command, acceptance
- [ ] **PLAN-07**: No step may require "research" without specifying the artifact to produce
- [ ] **PLAN-08**: handoff_to_builder includes branch_name_hint, commit_message_hint, pr_title, pr_body_outline

### Risk Classification

- [ ] **PLAN-09**: Planner sets risk_level HIGH when touch_paths include: .github/workflows/**, infra/**, terraform/**, iam/**, deploy scripts, lockfiles, migrations
- [ ] **PLAN-10**: Planner sets risk_level MEDIUM when touch_paths include dependency manifests (pyproject.toml, requirements*.txt, package.json, etc.)
- [ ] **PLAN-11**: Planner sets risk_level LOW otherwise
- [ ] **PLAN-12**: risk_level and touch_paths align with file-change intent (advisory; Governor/Security enforce their own rules)

### Triggering

- [ ] **PLAN-13**: Planner triggers on GitHub issue opened with label `agent:plan`
- [ ] **PLAN-14**: Planner triggers on manual CLI: `booty plan --issue <n>`
- [ ] **PLAN-15**: Planner triggers on manual CLI: `booty plan --text "..."`

### Output Delivery

- [ ] **PLAN-16**: Planner posts plan as issue comment (JSON in code block)
- [ ] **PLAN-17**: Planner stores artifact in `$HOME/.booty/state/plans/<issue_id>.json`
- [ ] **PLAN-18**: Issue comment includes Goal, Risk level, Step list (P1..Pn), "Builder instructions" section — avoid long prose

### Builder Contract

- [ ] **PLAN-19**: Plan specifies file paths/globs Builder must touch
- [ ] **PLAN-20**: Plan specifies exact commands to run (tests/lint) where possible
- [ ] **PLAN-21**: Plan specifies acceptance criteria per step ("done" definition)
- [ ] **PLAN-22**: Builder can execute the plan without needing clarifications

### Idempotency

- [ ] **PLAN-23**: For same issue within 24h, Planner produces same plan unless inputs changed
- [ ] **PLAN-24**: Plan includes plan_hash (hash of normalized plan) in metadata for dedup

### Acceptance

- [ ] **PLAN-25**: Given a real issue, Planner emits valid Plan JSON within the schema
- [ ] **PLAN-26**: Output is reproducible for unchanged inputs

## Future Requirements (v1.x+)

Deferred to later milestones.

- Builder integration: consume plan from comment/artifact when agent:builder label added
- Observability incident → Planner → Builder flow (vs current Observability → issue with agent:builder)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Code changes by Planner | Planner produces plan only; Builder executes |
| PR creation by Planner | Builder owns PR creation |
| Auto-approval | Operator reviews and approves |
| Architecture redesign proposals | Plan scope is implementation steps, not design |
| plan_version > 1 | Single schema for v1.7 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PLAN-01 | 28 | Pending |
| PLAN-02 | 28 | Pending |
| PLAN-03 | 28 | Pending |
| PLAN-04 | 28 | Pending |
| PLAN-05 | 27, 29 | Pending |
| PLAN-06 | 27, 29 | Pending |
| PLAN-07 | 27, 29 | Pending |
| PLAN-08 | 27, 29 | Pending |
| PLAN-09 | 29 | Pending |
| PLAN-10 | 29 | Pending |
| PLAN-11 | 29 | Pending |
| PLAN-12 | 29 | Pending |
| PLAN-13 | 27 | Pending |
| PLAN-14 | 27 | Pending |
| PLAN-15 | 27 | Pending |
| PLAN-16 | 30 | Pending |
| PLAN-17 | 27, 30 | Pending |
| PLAN-18 | 30 | Pending |
| PLAN-19 | 29 | Pending |
| PLAN-20 | 29 | Pending |
| PLAN-21 | 29 | Pending |
| PLAN-22 | 29 | Pending |
| PLAN-23 | 31 | Pending |
| PLAN-24 | 31 | Pending |
| PLAN-25 | 29 | Pending |
| PLAN-26 | 31 | Pending |

**Coverage:**
- v1.7 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-16*
*Last updated: 2026-02-16 after Planner spec*
