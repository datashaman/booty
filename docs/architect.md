# Architect Agent (v1.8)

Validates and refines plans before Builder executes. Sits between Planner and Builder, prevents structurally risky work, enforces architectural consistency. Architect does not write code — it rewrites the plan when necessary.

## Config (.booty.yml)

```yaml
architect:
  enabled: true
  rewrite_ambiguous_steps: true
  enforce_risk_rules: true
```

- **enabled** — When true, Builder runs only after Architect approval. Default: true.
- **rewrite_ambiguous_steps** — Rewrite vague step instructions. Default: true.
- **enforce_risk_rules** — Recompute risk from touch_paths (HIGH/MEDIUM/LOW). Default: true.

## Env overrides

- `ARCHITECT_ENABLED` — 1/true/yes or 0/false/no
- `ARCHITECT_CACHE_TTL_HOURS` — Cache reuse window (default: 24)

## CLI

```bash
booty architect status [--repo owner/repo] [--json]   # 24h metrics
booty architect review --issue N [--repo owner/repo]   # Force re-evaluation; exit 1 on block
```

## Flow

1. Planner completes → Architect runs (when enabled)
2. Architect validates: structural, paths, risk, ambiguity, overreach
3. Approved → Persist to `~/.booty/state/plans/<owner>/<repo>/<issue>-architect.json`; enqueue Builder
4. Blocked → Post comment, apply `agent:architect-review` label; do NOT enqueue Builder

## Metrics

Persisted under `~/.booty/state/architect/metrics.json`:

- plans_approved — Approved without rewrite
- plans_rewritten — Approved after rewrite
- plans_blocked — Blocked
- cache_hits — Reused cached result within 24h
