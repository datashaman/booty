# Phase 29: Plan Generation - Research

**Researched:** 2026-02-16
**Domain:** LLM-based Plan JSON generation from PlannerInput; deterministic risk classification
**Confidence:** HIGH

## Summary

Phase 29 produces valid Plan JSON from normalized PlannerInput (Phase 28) using a Magentic LLM prompt that returns the existing Plan Pydantic model. Risk classification is applied deterministically via PathSpec matching on touch_paths after the LLM returns. The project already uses Magentic with `@prompt` and Pydantic return types (CodeGenerationPlan, IssueAnalysis), and PathSpec for risk scoring (release_governor/risk.py). CONTEXT.md locks step granularity, risk rules (highest wins, exclude docs), touch_paths derivation, and handoff_to_builder format.

**Primary recommendation:** Add `generate_plan(PlannerInput) -> Plan` Magentic prompt in `planner/generation.py`; add `planner/risk.py` with `classify_risk_from_paths(touch_paths) -> tuple[Literal, list[str]]` using PathSpec; wire worker to call generation → classify → store. Use Field descriptions and few-shot examples in prompt for step structure. Exclude docs/README from risk per CONTEXT.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| magentic | (existing) | LLM prompt, structured Plan output | Already used for CodeGenerationPlan; Pydantic return types validated |
| pydantic | (existing) | Plan, Step, HandoffToBuilder schema | Schema in schema.py; magentic sends JSON schema to LLM |
| pathspec | (existing) | Path matching for risk classification | Already used in risk.py, limits.py; gitwildmatch semantics |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | (existing) | Retry on rate limit/timeout | Use same pattern as llm/prompts.py for LLM calls |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| magentic @prompt | Raw Anthropic API | Magentic gives schema-to-LLM, retries; hand-rolling loses that |
| PathSpec | fnmatch/glob | PathSpec handles ** recursion; project standard |
| Post-LLM risk | LLM-assigned risk | CONTEXT locks "LLM never overrides"; rules-based only |

## Architecture Patterns

### Recommended Project Structure

```
src/booty/planner/
├── schema.py         # (existing) Plan, Step, HandoffToBuilder
├── input.py         # (existing) PlannerInput, normalizers
├── risk.py          # NEW: classify_risk_from_paths, default HIGH/MEDIUM patterns
├── generation.py    # NEW: generate_plan(PlannerInput) -> Plan
├── config.py        # (existing) PlannerConfig — extend with high_risk_paths, medium_risk_paths optional
├── worker.py        # (existing) process_planner_job — call generation, classify, store
├── store.py         # (existing)
└── jobs.py          # (existing)
```

### Pattern 1: Magentic Structured Output for Plan

**What:** `@prompt` decorated function with Plan (Pydantic) as return type; magentic serializes schema to LLM; response validated by Pydantic.
**When to use:** Any LLM call needing strict JSON output.
**Example:**
```python
# Source: magentic.dev/structured-outputs
from magentic import prompt
from booty.planner.schema import Plan

@prompt("""
Create a Plan for: {goal}

Body:
{body}

{repo_tree}

Output a Plan with max 12 steps (P1..P12).
Each step: id, action (read|edit|add|run|verify), path or command, acceptance.
""")
def generate_plan(goal: str, body: str, repo_tree: str) -> Plan: ...
```

**Enhancements:** Use `Field(description=...)` on Plan/Step/HTOB for better LLM guidance. Add few-shot step examples in prompt.

### Pattern 2: Deterministic Risk from touch_paths

**What:** After LLM returns Plan with touch_paths, run pure function over paths; PathSpec.match_file per path; HIGH wins, else MEDIUM, else LOW. Exclude docs/README.
**When to use:** CONTEXT-locked "purely rules-based; LLM never overrides."
**Example:**
```python
# Adapted from release_governor/risk.py
from pathspec import PathSpec

HIGH_DEFAULT = [".github/workflows/**", "infra/**", "terraform/**", "**/migrations/**", "**/*lock*"]
MEDIUM_DEFAULT = ["**/pyproject.toml", "**/requirements*.txt", "**/package.json", "**/Cargo.toml"]
EXCLUDE_FROM_RISK = ["docs/**", "README*", "*.md"]

def classify_risk_from_paths(touch_paths: list[str]) -> tuple[Literal["LOW","MEDIUM","HIGH"], list[str]]:
    if not touch_paths:
        return "HIGH", []  # CONTEXT: empty -> HIGH (unknown scope)
    exclude = PathSpec.from_lines("gitwildmatch", EXCLUDE_FROM_RISK)
    high_spec = PathSpec.from_lines("gitwildmatch", HIGH_DEFAULT)
    medium_spec = PathSpec.from_lines("gitwildmatch", MEDIUM_DEFAULT)
    drivers: list[str] = []
    max_risk = "LOW"
    for p in touch_paths:
        if exclude.match_file(p):
            continue
        if high_spec.match_file(p):
            return "HIGH", [p] + [x for x in touch_paths if high_spec.match_file(x) and x != p]
        if medium_spec.match_file(p):
            max_risk = "MEDIUM"
            drivers.append(p)
    return max_risk, drivers
```

### Anti-Patterns to Avoid

- **LLM-assigned risk_level:** CONTEXT locks rules-based; derive from touch_paths only.
- **Inferring touch_paths from run commands:** CONTEXT says only read/edit/add step paths.
- **Research steps without artifact:** PLAN-07 forbids; prompt must require artifact path.
- **Hand-rolling path matching:** Use PathSpec; don't use fnmatch/regex.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| JSON schema for LLM | Manual prompt instructions | Pydantic model as return type | Magentic auto-generates; validation built-in |
| Path matching | Custom glob logic | PathSpec.from_lines("gitwildmatch", patterns) | Project standard; ** support |
| Retry/backoff | Custom retry loop | tenacity + magentic max_retries | Same as llm/prompts.py |

## Common Pitfalls

### Pitfall 1: LLM Returns Invalid Step IDs
**What goes wrong:** Step ids like "step1" or "1" fail Plan validation (pattern `^P\d+$`).
**Why it happens:** LLM may not follow P1..P12 format.
**How to avoid:** Prompt explicitly: "Step ids must be P1, P2, ... P12." Add Field(description="Step id P1..P12") on Step.id.
**Warning signs:** StructuredOutputError or ValidationError on Plan parse.

### Pitfall 2: touch_paths vs steps Mismatch
**What goes wrong:** touch_paths not union of read/edit/add step paths.
**Why it happens:** LLM may add extra paths or omit some.
**How to avoid:** Post-process: derive touch_paths = union of step.path for action in (read,edit,add); overwrite LLM touch_paths before risk classification.
**Warning signs:** Risk classification incorrect; Builder gets wrong file set.

### Pitfall 3: Body Length Overflow
**What goes wrong:** Unbounded body wastes tokens (Phase 28 already trims to 8k).
**Why it happens:** Very long issues.
**How to avoid:** Phase 28 BODY_TRIM_CHARS=8000; ensure PlannerInput passed to prompt uses trimmed body.
**Warning signs:** Token budget exceeded; slow/expensive calls.

### Pitfall 4: Research Steps Without Artifact
**What goes wrong:** Plan has step action="read" or vague "research" with no path/artifact.
**Why it happens:** LLM produces exploratory steps.
**How to avoid:** Prompt: "Any exploratory step MUST declare path to artifact (file to read or create). No vague 'look into...' steps."
**Warning signs:** PLAN-07 violated; Builder cannot execute.

## Code Examples

### Magentic Prompt with Few-Shot Steps

```python
# planner/generation.py
STEP_EXAMPLE = """
Example steps:
- P1: read, path=src/auth/config.py, acceptance="Understand current config"
- P2: edit, path=src/auth/config.py, acceptance="Add validation setting"
- P3: run, command="pytest tests/test_auth.py", acceptance="All tests pass"
"""

@prompt("""
You are a Planner. Create an execution plan from the request below.

Goal: {goal}

Body:
{body}

Repo tree (if available):
{repo_tree}

RULES:
1. Max 12 steps. Ids: P1, P2, ... P12.
2. Actions: read | edit | add | run | verify
3. For read/edit/add: provide path. For run/verify: provide command.
4. Every step needs acceptance (how to verify done).
5. No research without artifact path.
6. handoff_to_builder: branch_name_hint (e.g. issue-123-slug), commit_message_hint (conventional), pr_title, pr_body_outline.

{step_example}
""")
def _generate_plan_impl(goal: str, body: str, repo_tree: str, step_example: str) -> Plan: ...
```

### Derive touch_paths from Steps

```python
def derive_touch_paths(steps: list[Step]) -> list[str]:
    paths: set[str] = set()
    for s in steps:
        if s.action in ("read", "edit", "add") and s.path:
            paths.add(s.path.strip("/"))
    return sorted(paths)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual JSON prompting | Pydantic return type + Magentic | project start | Schema validation, retries |
| LLM-assigned risk | Deterministic PathSpec | CONTEXT lock | Predictable, auditable |

## Open Questions

1. **Planner-specific risk paths vs Governor reuse**
   - What we know: Governor has high_risk_paths, medium_risk_paths in ReleaseGovernorConfig.
   - What's unclear: Should Planner have its own config block (planner.high_risk_paths) or reuse?
   - Recommendation: Add optional planner.high_risk_paths, planner.medium_risk_paths; default to PLAN-09/10 patterns. Enables Planner-specific tuning without coupling to Governor.

## Sources

### Primary (HIGH confidence)
- magentic.dev/structured-outputs — Pydantic return types, Field descriptions
- src/booty/llm/prompts.py — Existing magentic usage
- src/booty/release_governor/risk.py — PathSpec risk classification pattern

### Secondary (MEDIUM confidence)
- .planning/phases/15-trigger-risk-decision-logic/15-RESEARCH.md — PathSpec risk pattern

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — magentic, pathspec already in use
- Architecture: HIGH — CONTEXT locks most decisions
- Pitfalls: MEDIUM — LLM behavior varies; validation catches schema issues

**Research date:** 2026-02-16
**Valid until:** 30 days
