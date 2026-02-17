# Routing Logic

Plan-state-first routing for `issues.labeled` and `issues.opened` with the trigger label. The router resolves plan state via `get_plan_for_builder`, then routes to **Planner** | **Architect** | **Builder**.

**Implementation:** `src/booty/router/router.py` `_route_issues`

---

## Overview

When an issue receives the trigger label (or is opened with it), the router:

1. Resolves plan state: Architect artifact first, then Planner plan (when `builder_compat` enabled)
2. Routes based on plan state and agent config:
   - **Architect-approved plan** → Builder
   - **Unreviewed plan** (Planner plan, no Architect artifact) → Architect
   - **No plan** → Planner

---

## Decision Table

| Plan state | Architect enabled | Action |
|------------|-------------------|--------|
| Architect-approved | yes | Builder |
| Unreviewed (Planner plan) | yes | Architect |
| No plan | yes | Planner |
| Plan exists (any) | no | Builder (Architect skipped) |
| No plan | no | Planner |

---

## Config Precedence

**Precedence:** env overrides file; file overrides default.

| Flag | Env var | File (.booty.yml) | Default |
|------|---------|-------------------|---------|
| Architect enabled | `ARCHITECT_ENABLED` (1/true/yes, 0/false/no) | `architect.enabled` | `true` |
| builder_compat | `ARCHITECT_BUILDER_COMPAT` (1/true/yes, 0/false/no) | `architect.builder_compat` | `true` |
| Planner enabled | `PLANNER_ENABLED` | — | `true` |

---

## builder_compat

When `builder_compat` is **true** (default), Builder can use a Planner plan when no Architect artifact exists. This allows migration: repos can run Builder with Planner-only plans during rollout.

When `builder_compat` is **false**, Builder requires an Architect artifact. Unreviewed (Planner) plans route to Architect, not Builder.

---

## Disabled-Agent Matrix

| Architect | Planner | Plan state | Action |
|-----------|---------|------------|--------|
| enabled | enabled | Architect-approved | Builder |
| enabled | enabled | Unreviewed | Architect |
| enabled | enabled | No plan | Planner |
| enabled | disabled | Architect-approved | Builder |
| enabled | disabled | Unreviewed | Architect |
| enabled | disabled | No plan | `builder_blocked` comment, no enqueue |
| disabled | enabled | Plan exists (any) | Builder (compat allows Planner plan) |
| disabled | enabled | No plan | Planner |
| disabled | disabled | Plan exists | Builder |
| disabled | disabled | No plan | `builder_blocked` comment, no enqueue |

---

## Dedup Keys

| Agent | Dedup key |
|-------|-----------|
| Planner | `(repo_full_name, delivery_id)` |
| Architect | `(repo_full_name, plan_hash)` |
| Builder | `(repo_full_name, delivery_id)` or `(repo_full_name, issue_number)` for issue-driven |

---

## Event Prerequisites

- **issues.labeled** or **issues.opened** with trigger label
- `has_trigger_label` must be true; otherwise event is ignored with `not_plan_or_builder_trigger`

---

## Related

- [Planner](planner.md)
- [Architect](architect.md)
- [Builder](builder-planner-integration-audit.md)
