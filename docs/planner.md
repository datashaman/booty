# Planner Agent

Produces structured execution plans from GitHub issues, Observability incidents, or operator CLI input. Plans specify goal, steps, risk level, touch paths, and handoff metadata for the Builder. Does not make code changes or create PRs.

## Overview

The Planner Agent:

- **Accepts** GitHub issues (label `agent:plan`), Observability incident format, or free text via `booty plan --text "..."`
- **Produces** Plan JSON conforming to schema (goal, steps, risk_level, touch_paths, handoff_to_builder)
- **Posts** plan as issue comment and stores to `~/.booty/state/plans/`
- **Caches** same input within 24h returns cached plan (no LLM call)

## Triggers

| Trigger | How |
|---------|-----|
| GitHub issue | Label `agent:plan` on opened or labeled |
| CLI issue | `booty plan --issue <n> --repo owner/repo` |
| CLI text | `booty plan --text "fix login validation"` |

## Configuration

Optional `planner` block in `.booty.yml`:

```yaml
planner:
  enabled: true
```

**Env overrides:** `PLANNER_ENABLED`, `PLANNER_STATE_DIR`, `PLANNER_CACHE_TTL_HOURS`

## CLI reference

### booty plan --issue

Generate plan from a GitHub issue. Requires `GITHUB_TOKEN`.

```bash
booty plan --issue 42 --repo owner/repo
```

### booty plan --text

Generate plan from free text. Same text within 24h returns cached plan; output shows `(cached, created at …)`.

```bash
booty plan --text "add auth validation to login endpoint"
```

## Output format

Plan JSON includes:
- **goal** — One-line objective
- **steps** — P1..Pn with action (read/edit/add/run/verify), path/command, acceptance
- **risk_level** — LOW, MEDIUM, or HIGH (from touch_paths)
- **handoff_to_builder** — branch_name_hint, commit_message_hint, pr_title, pr_body_outline

Comment on the issue includes Goal, Risk, Step list, and Builder instructions.

## Idempotency

- Same issue input within 24h → cached plan, no LLM call
- Same free-text input within 24h → cached plan, `(cached, created at …)` in CLI output
- Plan metadata: `created_at`, `input_hash`, `plan_hash` (for dedup)

---

*See [github-app-setup.md](github-app-setup.md) for webhook events; Issues event triggers Planner when `agent:plan` is present.*
