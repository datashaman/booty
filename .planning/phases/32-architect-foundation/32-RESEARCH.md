# Phase 32: Architect Foundation - Research

**Researched:** 2026-02-17
**Domain:** Booty internal — Architect config, Planner→Architect→Builder flow, input ingestion
**Confidence:** HIGH

## Summary

Phase 32 establishes Architect Agent foundation: ArchitectConfig in .booty.yml (enabled, rewrite_ambiguous_steps, enforce_risk_rules), Architect triggering from Planner completion (never from GitHub labels), input ingestion (plan_json, normalized_input, optional repo_context, issue_metadata), and failure handling (unknown keys fail Architect only). All patterns exist: PlannerConfig (27-02), SecurityConfig, Planner worker→Builder enqueue (main.py L308–331), and load_booty_config_from_content via GitHub API (webhooks, memory ingestion). Architect runs synchronously after Planner; when enabled and config valid, it receives the plan and either approves (enqueue Builder) or blocks (post comment, apply agent:architect-review, don't enqueue). Unknown keys in architect block: validate at Architect invocation; don't crash BootyConfig load.

**Primary recommendation:** Mirror PlannerConfig for ArchitectConfig; insert Architect call in Planner worker after save_plan, before Builder enqueue; load .booty.yml from repo via GitHub API where worker has owner/repo.

## Standard Stack

### Core (existing)
| Component | Purpose | Source |
|-----------|---------|--------|
| Pydantic | ArchitectConfig, extra="forbid" | planner/config.py, security/runner |
| Plan | plan_json structure | planner/schema.py |
| PlannerInput | normalized_input | planner/input.py |
| load_booty_config_from_content | .booty.yml from YAML string | test_runner/config.py |

### Config Block Pattern
| Pattern | Example | Use |
|---------|---------|-----|
| ArchitectConfig extra="forbid" | PlannerConfig, SecurityConfig | Unknown keys fail validation |
| architect: dict \| None | memory block | Raw in BootyConfigV1; validate at Architect invocation |
| get_architect_config | get_planner_config | Returns ArchitectConfig \| None; raises ArchitectConfigError on unknown keys |
| apply_architect_env_overrides | apply_planner_env_overrides | ARCHITECT_ENABLED only (per CONTEXT) |

### Planner Worker Flow (current)
```
planner_queue.get() → process_planner_job(job) → save_plan → post_plan_comment
  → enqueue Builder (job_queue.enqueue)
```

### Planner Worker Flow (Phase 32)
```
planner_queue.get() → process_planner_job(job) → save_plan → post_plan_comment
  → [if cache hit: skip Architect, enqueue Builder]
  → [else: load booty_config from repo]
  → get_architect_config(booty_config)
  → [if ArchitectConfigError: post block comment, apply agent:architect-review, don't enqueue]
  → [if config None or enabled=False: enqueue Builder]
  → [else: process_architect_input(...) → if approved enqueue Builder, else block]
```

## Architecture Patterns

### ArchitectConfig (mirror PlannerConfig)
```python
class ArchitectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    rewrite_ambiguous_steps: bool = True
    enforce_risk_rules: bool = True
```

### Unknown Keys Handling (Architect-only failure)
- BootyConfigV1.architect: dict | None (raw, like memory)
- get_architect_config(booty_config) -> ArchitectConfig
  - If architect is None: return None (Architect disabled)
  - If architect dict: try ArchitectConfig.model_validate(architect)
    - Success: return ArchitectConfig
    - ValidationError (e.g. unknown key): raise ArchitectConfigError
- Planner worker catches ArchitectConfigError → post comment, apply label, don't enqueue Builder
- BootyConfig loads successfully; only Architect path fails

### Load .booty.yml in Worker
```python
# Planner worker has: job.owner, job.repo, get_settings().GITHUB_TOKEN
from github import Auth, Github
g = Github(auth=Auth.Token(token))
gh_repo = g.get_repo(f"{owner}/{repo}")
default_branch = gh_repo.default_branch or "main"
fc = gh_repo.get_contents(".booty.yml", ref=default_branch)
yaml_content = fc.decoded_content.decode()
booty_config = load_booty_config_from_content(yaml_content)
```

### Architect Input Structure
```python
class ArchitectInput(BaseModel):
    plan: Plan | dict  # plan_json
    normalized_input: PlannerInput  # from normalize_from_job
    repo_context: dict | None = None
    issue_metadata: dict | None = None  # from job.payload["issue"] or similar
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Config block validation | Custom parsing | ArchitectConfig.model_validate with extra="forbid" |
| .booty.yml fetch | Custom HTTP | gh_repo.get_contents (existing in webhooks, security) |
| Plan serialization | Custom JSON | plan.model_dump() / Plan.model_validate() |
| Comment posting | Custom API | post_plan_comment pattern; need post_architect_block_comment |

## Common Pitfalls

### Config Load Scope
**Pitfall:** Validating architect block at BootyConfigV1 parse time with extra="forbid" would fail entire config load for typo in one repo.
**Fix:** Keep architect as raw dict; validate in get_architect_config which is only called when Architect path runs. ValidationError → ArchitectConfigError → Planner worker handles.

### Planner Cache Hit
**Pitfall:** Running Architect on cache hit when plan unchanged.
**Fix:** CONTEXT: "Architect runs only when plan changes; Planner cache hit → skip Architect". In process_planner_job, when cached plan is used, skip Architect and enqueue Builder directly.

### Missing repo_context
**Pitfall:** Assuming repo_context always present.
**Fix:** ARCH-05: Architect must operate when repo_context is missing. process_architect_input accepts repo_context=None; Phase 33 validation will handle degraded mode.

## Code Examples

### PlannerConfig (planner/config.py)
```python
class PlannerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True

def get_planner_config(booty_config: object) -> PlannerConfig | None:
    planner = getattr(booty_config, "planner", None)
    if planner is None:
        return None
    return PlannerConfig.model_validate(planner)
```

### Planner worker Builder enqueue (main.py L308–331)
```python
if job_queue and not job_queue.has_issue_in_queue(job.repo_url, job.issue_number):
    builder_job = Job(...)
    enqueued = await job_queue.enqueue(builder_job)
```

### Webhooks load .booty.yml (webhooks.py)
```python
fc = repo.get_contents(".booty.yml", ref=repo.default_branch or "main")
config = load_booty_config_from_content(fc.decoded_content.decode())
```

## Open Questions

1. **Debounce:** CONTEXT mentions "Debounce Architect runs per issue within time window." Phase 32 can defer; Architect runs once per Planner completion.
2. **booty plan CLI:** Architect triggers from "booty plan CLI" per ARCH-02. CLI path may need Phase 32 or later wiring.
3. **agent:architect-review label:** GitHub API to add label — use existing label application pattern from Security/Verifier.

## Sources

### Primary (HIGH confidence)
- src/booty/planner/config.py — PlannerConfig, get_planner_config
- src/booty/planner/worker.py — process_planner_job flow
- src/booty/main.py — Planner worker loop, Builder enqueue after plan
- src/booty/test_runner/config.py — BootyConfigV1, validate_*_block, load_booty_config_from_content
- src/booty/webhooks.py — load .booty.yml from repo
- src/booty/planner/input.py — normalize_from_job, PlannerInput
- .planning/phases/32-architect-foundation/32-CONTEXT.md — Decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all internal, patterns in codebase
- Architecture: HIGH — direct extension of Planner worker flow
- Pitfalls: MEDIUM — CONTEXT decisions cover edge cases

**Research date:** 2026-02-17
**Valid until:** 30 days
