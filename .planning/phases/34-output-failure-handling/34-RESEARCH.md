# Phase 34: Output & Failure Handling - Research

**Researched:** 2026-02-17
**Domain:** Architect output shape, GitHub comment updates, block handling
**Confidence:** HIGH

## Summary

Phase 34 delivers ArchitectPlan output, updates the plan comment with a `<!-- booty-architect -->` section, and handles block cases by updating the same comment (not creating new). All patterns exist in the codebase: `Plan` schema, `format_plan_comment`, `post_plan_comment` (find-and-edit), `post_architect_blocked_comment`. The phase refines ArchitectResult into ArchitectPlan (ARCH-16), changes block handling from new-comment to same-comment update (ARCH-19, per 34-CONTEXT), and wires comment updates for Approved/Rewritten/Blocked states. No new libraries or external APIs.

**Primary recommendation:** Add ArchitectPlan dataclass; add `format_architect_section()` and `update_plan_comment_with_architect_section()`; refactor `post_architect_blocked_comment` to update same comment; wire main.py to update comment on approved/rewritten/blocked.

## Standard Stack

| Component | Purpose |
|-----------|---------|
| Plan (planner/schema.py) | Source for plan_version, goal, steps, touch_paths, risk_level, handoff_to_builder |
| format_plan_comment (planner/output.py) | Template for comment structure; booty-architect inserts between Builder instructions and `<details>` |
| post_plan_comment (comments.py) | Find-and-edit; single plan comment per issue |
| PyGithub | comment.edit(), issue.get_comments() — existing |

No new dependencies.

## Architecture Patterns

### ArchitectPlan vs ArchitectResult

- **ArchitectResult** (Phase 32): approved, plan, architect_notes. Used for approval flow.
- **ArchitectPlan** (Phase 34, ARCH-16): plan_version, goal, steps, touch_paths, risk_level, handoff_to_builder, architect_notes. Structured output for Builder handoff (Phase 36) and comment display.
- Build ArchitectPlan from validated Plan: all fields map from Plan; architect_notes from ArchitectResult.

### Comment Update Pattern

**Approved/Rewritten:** main.py has plan. Build full body: format_plan_comment(plan) + architect section. Use inject pattern: insert architect block between "## Builder instructions" section and `<details>`. Then post_plan_comment(body).

**Blocked:** Planner already posted comment. Fetch existing comment body (find `<!-- booty-plan -->`), inject booty-architect Blocked section at same position, edit comment. Requires `update_plan_comment_with_architect_section` or equivalent that finds comment, modifies body, edits.

### Section Injection Point

Current format_plan_comment structure:
```
## Goal
## Risk
## Steps
## Builder instructions
<details>Full plan (JSON)</details>
<!-- booty-plan -->
```

CONTEXT: booty-architect "between Builder instructions, before collapsed JSON". Insert before `<details><summary>Full plan`.

## Don't Hand-Roll

| Problem | Use | Why |
|---------|-----|-----|
| GitHub comment edit | PyGithub comment.edit() | Already used by post_plan_comment, post_memory_comment |
| Plan structure | Plan from planner/schema | ARCH-16 fields come from Plan |
| Find comment | issue.get_comments() + marker scan | Same as post_plan_comment |

## Common Pitfalls

### Block creates new comment

- **Current:** post_architect_blocked_comment creates new comment (Phase 32).
- **Required (34-CONTEXT):** Block updates same plan comment. Operators need failed plan visible.
- **Fix:** Replace post_architect_blocked_comment with flow that fetches plan comment, injects booty-architect Blocked section, edits.

### architect_notes truncation

- **Per CONTEXT:** First line inline; remainder in `<details>`. Omit if empty.
- **Pitfall:** Dumping full notes can overwhelm comment. Use first-line + details pattern.

### Blocked message format

- **Exact phrase (ARCH-19):** "Architect review required — plan is structurally unsafe."
- **Plus short reason:** e.g. "Steps > 12", "Overreach unresolved". Already in _block() with parenthetical.

## Code Examples

### format_plan_comment structure (planner/output.py)

```python
# Current: sections joined, ends with <!-- booty-plan -->
# Add architect_section param: insert before <details>
sections.append("## Builder instructions\n\n" + "\n".join(bullets))
if architect_section:
    sections.append(architect_section)
sections.append("<details>...")
```

### Finding and editing plan comment (comments.py pattern)

```python
for comment in issue.get_comments():
    if "<!-- booty-plan -->" in (comment.body or ""):
        # Modify body: inject architect section before <details>
        new_body = inject_architect_section(comment.body, architect_section)
        comment.edit(new_body)
        return
```

### ArchitectPlan from Plan

```python
def build_architect_plan(plan: Plan, architect_notes: str | None) -> ArchitectPlan:
    return ArchitectPlan(
        plan_version=plan.plan_version,
        goal=plan.goal,
        steps=plan.steps,
        touch_paths=plan.touch_paths,
        risk_level=plan.risk_level,
        handoff_to_builder=plan.handoff_to_builder,
        architect_notes=architect_notes,
    )
```

## State of the Art

| Current | Phase 34 | Impact |
|---------|----------|--------|
| ArchitectResult(approved, plan, notes) | ArchitectPlan when approved; ArchitectResult for flow | ARCH-16 structured output |
| post_architect_blocked_comment creates new | Update same plan comment | Single source of truth |
| No architect section in plan comment | <!-- booty-architect --> Approved/Rewritten/Blocked | Operator visibility |

## Open Questions

None — CONTEXT.md and requirements fully specify implementation.

## Sources

### Primary (HIGH confidence)
- Codebase: src/booty/architect/worker.py, src/booty/github/comments.py, src/booty/planner/output.py, src/booty/main.py
- .planning/phases/34-output-failure-handling/34-CONTEXT.md
- .planning/REQUIREMENTS.md ARCH-16 through ARCH-22

### Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components exist in codebase
- Architecture: HIGH — patterns from Phase 30, 32, 33
- Pitfalls: HIGH — CONTEXT specifies block behavior change

**Research date:** 2026-02-17
**Valid until:** 30 days (stable internal integration)
