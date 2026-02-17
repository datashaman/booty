# Phase 33: Validation Rules - Research

**Researched:** 2026-02-17
**Domain:** Rule-driven plan validation, path-based risk classification
**Confidence:** HIGH

## Summary

Phase 33 implements validation rules for the Architect agent. The work is entirely rule-driven (no LLM), using pure Python validation logic against the existing Plan schema. The Planner already defines `Step`, `Plan`, and `derive_touch_paths` in `planner/schema.py` and `planner/generation.py`. Architect receives `ArchitectInput(plan, ...)` where plan is `Plan | dict` and returns `ArchitectResult(approved, plan, architect_notes)`.

Research confirms: no new libraries required. Validation follows a pipeline pattern (structural → path → risk → ambiguity → overreach). Path-based risk uses simple prefix/suffix matching. Ambiguity and overreach use regex/keyword patterns. CONTEXT.md locks implementation decisions; this research documents patterns and pitfalls.

**Primary recommendation:** Implement validation as a pipeline of rule functions returning validation results; each rule returns pass | fail | rewrite. Consolidate into `validate_plan()` that returns (approved, plan_or_rewrite, notes).

## Standard Stack

### Core
| Component | Purpose | Why Standard |
|-----------|---------|--------------|
| Pydantic Plan/Step | Plan structure | Already in codebase |
| `derive_touch_paths` pattern | Path union | Planner has it; Architect reuses |
| Python `re` module | Ambiguity/overreach patterns | Stdlib, no deps |

### Don't Hand-Roll
| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema validation | Custom parser | Pydantic Plan/Step | Already exists |
| Path matching | Custom DSL | `re.match`, `str.startswith` | Stdlib sufficient |
| Risk classification | External service | In-memory rules | < 5s target, no I/O |

## Architecture Patterns

### Validation Pipeline Pattern
**What:** Sequential rule functions; first failure can short-circuit or collect all.
**When:** Multiple independent validations (structural, path, risk, ambiguity, overreach).
**Example:**
```python
def validate_structural(plan: Plan) -> ValidationResult: ...
def validate_paths(plan: Plan) -> ValidationResult: ...
def validate_risk(plan: Plan, config: ArchitectConfig) -> ValidationResult: ...
# Orchestrator: run in order, stop on block or collect flags
```

### Risk from Paths (REQUIREMENTS ARCH-11)
**Rules:**
- HIGH: `.github/workflows/`, `infra/`, `migrations`, lockfiles (`package-lock.json`, `yarn.lock`, `uv.lock`, `poetry.lock`, `Cargo.lock`)
- MEDIUM: manifests (`pyproject.toml`, `package.json`, `requirements.txt`, `Cargo.toml`, etc.)
- LOW: else

**Pattern:** Iterate touch_paths, match prefixes/suffixes, take max severity.

## Common Pitfalls

### Pitfall 1: Plan as dict vs Plan instance
**What goes wrong:** ArchitectInput.plan can be `Plan | dict`. Pydantic validation only runs on Plan. Dict may have extra keys or wrong types.
**How to avoid:** Normalize to Plan early; use `Plan.model_validate(plan)` if dict. Catch ValidationError for structural reject.

### Pitfall 2: touch_paths recomputation vs existing
**What goes wrong:** Planner may set touch_paths; Architect must recompute and override if different (ARCH-12). Forgetting to update plan.touch_paths before returning causes drift.
**How to avoid:** Always compute from steps; always assign to plan before approval.

### Pitfall 3: Rewrite retry loop
**What goes wrong:** CONTEXT says "validation failure after rewrite: retry once, then block." Infinite loop if rewrite produces invalid again.
**How to avoid:** Track rewrite count; max 1 retry.

## Code Examples

### derive_touch_paths (Planner — reuse logic)
```python
# planner/generation.py — Architect should include "research" action
# ARCH-08: actions ∈ {read, add, edit, run, verify, research}
# research: path required per CONTEXT
def derive_touch_paths(steps: list[Step]) -> list[str]:
    paths: set[str] = set()
    for s in steps:
        if s.action in ("read", "edit", "add", "research") and s.path:
            p = s.path.lstrip("/")
            if p:
                paths.add(p)
    return sorted(paths)
```

### Risk from path (pattern)
```python
def risk_from_path(p: str) -> Literal["LOW", "MEDIUM", "HIGH"]:
    pn = p.lower().replace("\\", "/")
    if any(pn.startswith(x) or x in pn for x in [".github/workflows/", "infra/", "migrations"]) or pn.endswith(("package-lock.json", "yarn.lock", "uv.lock", "poetry.lock", "Cargo.lock")):
        return "HIGH"
    if any(pn.endswith(x) or pn == x for x in ["pyproject.toml", "package.json", "requirements.txt", "Cargo.toml"]):
        return "MEDIUM"
    return "LOW"
```

## Open Questions

1. **Exact overreach thresholds:** CONTEXT defers "path-count and directory-spread thresholds" to planning. Recommendation: ≥8 touch_paths OR ≥3 domain buckets (src/, tests/, docs/, infra/, .github/) = overreach candidate.
2. **Ambiguity patterns:** "fix", "improve", "as needed", vague acceptance length. Recommendation: regex blacklist + min acceptance length (e.g. < 15 chars) as heuristic.

## Sources

### Primary (HIGH confidence)
- `src/booty/planner/schema.py` — Plan, Step schema
- `src/booty/planner/generation.py` — derive_touch_paths
- `src/booty/architect/` — current Architect structure
- `.planning/phases/33-validation-rules/33-CONTEXT.md` — implementation decisions

### Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps, existing schema
- Architecture: HIGH — pipeline pattern well-established
- Pitfalls: HIGH — from codebase inspection

**Research date:** 2026-02-17
**Valid until:** 30 days
