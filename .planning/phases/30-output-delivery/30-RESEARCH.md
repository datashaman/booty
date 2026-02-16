# Phase 30: Output Delivery - Research

**Researched:** 2026-02-16
**Domain:** GitHub issue comments, plan formatting, operator UX
**Confidence:** HIGH

## Summary

Phase 30 delivers the planner output in two places: (1) as a formatted comment on the GitHub issue, (2) as a stored artifact (already implemented in Phase 27). The comment format is fully specified in 30-CONTEXT.md — section order, markdown structure, collapsed JSON, Builder instructions layout. All patterns exist in the codebase: `comments.py` has `_get_repo`, `issue.create_comment`, and find-and-edit patterns (`post_memory_comment`, `post_verifier_failure_comment`). No new libraries or external APIs. Implementation is wiring and formatting.

**Primary recommendation:** Add `post_plan_comment` to `comments.py` following the CONTEXT format; wire worker and CLI plan --issue to call it. Use `<!-- booty-plan -->` marker for find-and-edit (single comment per issue).

## Standard Stack

| Component | Purpose |
|-----------|---------|
| PyGithub | Already in use — `issue.create_comment()`, `issue.get_comments()`, `comment.edit()` |
| comments.py | `_get_repo`, existing post_* functions |

No new dependencies.

## Architecture Patterns

### Comment Posting Pattern

Mirror `post_memory_comment` / `post_verifier_failure_comment`:
1. Get repo via `_get_repo(github_token, repo_url)`
2. Get issue via `repo.get_issue(issue_number)`
3. If find-and-edit: iterate `issue.get_comments()`, match marker, `comment.edit()`; else `issue.create_comment()`
4. Marker: `<!-- booty-plan -->` for single-comment-per-issue behavior

### Formatting Function

Separate `format_plan_comment(plan: Plan) -> str` that returns markdown. Keeps posting logic and formatting decoupled. Format per 30-CONTEXT: Goal → Risk → Steps → Builder instructions → `<details>` JSON.

## Don't Hand-Roll

| Problem | Use | Why |
|---------|-----|-----|
| GitHub API | PyGithub (existing) | Already integrated, no REST boilerplate |
| Repo parsing | `_get_repo` in comments.py | Reuse, consistent with other comments |

## Common Pitfalls

- **Missing token:** Worker and CLI need GITHUB_TOKEN. If missing, store plan but skip comment (log warning). Don't fail the whole job.
- **pr_body_outline length:** CONTEXT says "collapsed in its own `<details>` when long" — define threshold (e.g. >200 chars) or use newline count.
- **Empty handoff fields:** Omit entirely per CONTEXT. Check each field before rendering.

## Code Examples

### Existing comment pattern (post_memory_comment)

```python
for comment in issue.get_comments():
    if "<!-- booty-memory -->" in (comment.body or ""):
        comment.edit(full_body)
        return
issue.create_comment(full_body)
```

### Plan to markdown (conceptual)

```python
# Section order: Goal, Risk, Steps, Builder instructions, <details> JSON
# Steps: - P1: action path — acceptance
# Builder: - **Branch:** ... (omit if empty)
```

## Open Questions

None — CONTEXT has locked decisions; implementation is straightforward.

## Sources

- Existing: src/booty/github/comments.py, src/booty/planner/worker.py, 30-CONTEXT.md
- Plan schema: src/booty/planner/schema.py

**Research date:** 2026-02-16
**Valid until:** Stable (no external API changes)
