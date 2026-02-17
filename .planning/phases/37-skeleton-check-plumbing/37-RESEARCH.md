# Phase 37: Skeleton + Check Plumbing - Research

**Researched:** 2026-02-17
**Domain:** Reviewer agent plumbing (module skeleton, config, GitHub Checks, PR comments)
**Confidence:** HIGH

## Summary

Phase 37 establishes Reviewer plumbing without LLM or webhook wiring: module skeleton, ReviewerConfig schema, check run lifecycle (queued → in_progress → success/failure), and single PR comment upsert with `<!-- booty-reviewer -->` marker. All required patterns exist in the codebase: Verifier/Security check runs in `github/checks.py`, Architect/Security config schemas, and find-and-edit PR comment pattern in `post_memory_comment`/`post_plan_comment`. No new external libraries required.

**Primary recommendation:** Mirror Verifier for check runs, Architect for config (raw dict + isolated validation), Memory for PR comment find-and-edit.

## Standard Stack

### Core (already in use)
| Component | Purpose | Location |
|----------|---------|----------|
| PyGithub | GitHub API (checks, comments) | github/checks.py, github/comments.py |
| pydantic | Config validation | architect/config.py, test_runner/config.py |
| GitHub Checks API | Check run lifecycle | repo.create_check_run(), check_run.edit() |

### Supporting
| Component | Purpose | When to Use |
|----------|---------|-------------|
| github/checks.py | create_*_check_run, edit_check_run | Add create_reviewer_check_run |
| github/comments.py | post_*_comment (find-and-edit) | Add post_reviewer_comment |
| get_verifier_repo | App-auth Repository | Reuse for Reviewer (same App) |

**No new installations.** All dependencies already in project.

## Architecture Patterns

### Recommended Module Structure
```
src/booty/reviewer/
├── __init__.py      # reviewer_enabled, get_reviewer_config exports
├── config.py        # ReviewerConfig, ReviewerConfigError, get_reviewer_config, apply_reviewer_env_overrides
└── (runner in Phase 38)
```

### Pattern 1: Check Run Lifecycle (from Verifier)
**What:** create_check_run (queued) → edit_check_run (in_progress) → edit_check_run (completed, conclusion success/failure)
**When:** Any agent that publishes a GitHub check
**Source:** src/booty/github/checks.py, src/booty/verifier/runner.py

```python
# Create (queued)
check_run = repo.create_check_run(
    name="booty/reviewer",
    head_sha=head_sha,
    status="queued",
    output={"title": "Booty Reviewer", "summary": "Queued for review…"},
)
# Update (in_progress)
check_run.edit(status="in_progress", output={"title": "Booty Reviewer", "summary": "Reviewing PR diff…"})
# Complete
check_run.edit(status="completed", conclusion="success", output={...})
```

### Pattern 2: Isolated Config Validation (from Architect)
**What:** BootyConfigV1.reviewer as raw dict; validate at get_reviewer_config; unknown keys raise ReviewerConfigError; BootyConfig load never fails
**When:** Agent-specific config that must not break other agents
**Source:** src/booty/architect/config.py, test_runner/config.py BootyConfigV1.architect

```python
# BootyConfigV1.reviewer: dict | None (raw, like architect)
# get_reviewer_config(booty_config) -> ReviewerConfig | None
# Raises ReviewerConfigError on unknown keys; caller handles (check failure + comment)
```

### Pattern 3: PR Comment Find-and-Edit (from Memory)
**What:** Iterate issue.get_comments(), find first with marker, edit else create
**When:** Single updatable comment per PR
**Source:** src/booty/github/comments.py post_memory_comment, post_plan_comment

```python
for comment in issue.get_comments():
    if "<!-- booty-reviewer -->" in (comment.body or ""):
        comment.edit(full_body)
        return
issue.create_comment(full_body)
```

### Anti-Patterns to Avoid
- **Validating reviewer at BootyConfig load:** Would fail entire config for typo; use lazy validation at Reviewer invocation only
- **Creating new comments instead of edit:** Creates comment spam; use find-and-edit
- **Different auth for Reviewer checks:** Reuse get_verifier_repo (same GitHub App) — add reviewer-specific create_reviewer_check_run

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GitHub Checks API | Custom HTTP | PyGithub repo.create_check_run | Auth, rate limits, pagination handled |
| PR comment upsert | Poll + create | post_reviewer_comment (find-and-edit) | Idempotent, single comment |
| Config schema | Manual parsing | Pydantic ReviewerConfig | Validation, env overrides |

## Common Pitfalls

### Pitfall 1: Unknown Key Breaking Config Load
**What goes wrong:** Validating reviewer block at BootyConfigV1 parse fails entire repo config
**Why:** Typo in reviewer block breaks Verifier, Security, Governor
**How to avoid:** reviewer as raw dict; validate only in get_reviewer_config when Reviewer runs
**Warning signs:** BootyConfigV1.model_validate failing on .booty.yml with reviewer block

### Pitfall 2: Comment on Wrong Object
**What goes wrong:** post_reviewer_comment on issue_number vs pr_number
**Why:** PR comments use pr.as_issue() or repo.get_issue(pr_number) — issues and PRs share number space
**How to avoid:** PR comments: repo.get_issue(pr_number) — same as post_memory_comment
**Warning signs:** Comment appears on wrong PR or issue

### Pitfall 3: Check Run Name Mismatch
**What goes wrong:** Inconsistent check name (e.g. "Booty Reviewer" vs "booty/reviewer")
**Why:** GitHub displays context name; REV-04 requires `booty/reviewer`
**How to avoid:** name="booty/reviewer" (context), output.title="Booty Reviewer" (display)
**Source:** checks.py uses name="booty/verifier", output.title="Booty Verifier"

## Code Examples

### create_reviewer_check_run (extend checks.py)
```python
# Mirror create_check_run, create_security_check_run
# get_verifier_repo already exists; add reviewer_enabled check
# name="booty/reviewer", output default {"title": "Booty Reviewer", "summary": "Queued for review…"}
```

### post_reviewer_comment (new in comments.py)
```python
# Mirror post_memory_comment: repo.get_issue(pr_number), iterate get_comments(),
# find "<!-- booty-reviewer -->", edit else create. Body must include marker block.
```

### ReviewerConfig (new reviewer/config.py)
```python
class ReviewerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False  # disabled by default
    block_on: list[str] = Field(default_factory=list)  # overengineering, poor_tests, etc.
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Manual check run HTTP | PyGithub create_check_run | Handled |
| Multiple comments per agent | Find-and-edit single comment | Clean PRs |

**Deprecated/outdated:** None — patterns are current.

## Open Questions

1. **REVIEWER_ENABLED env override scope** — CONTEXT: "env override REVIEWER_ENABLED wins over file". Apply in apply_reviewer_env_overrides (like ARCHITECT_ENABLED). Resolved: mirror apply_architect_env_overrides.

## Sources

### Primary (HIGH confidence)
- src/booty/github/checks.py — create_check_run, create_security_check_run, edit_check_run
- src/booty/github/comments.py — post_memory_comment, post_plan_comment
- src/booty/architect/config.py — ArchitectConfig, get_architect_config, apply_architect_env_overrides
- src/booty/test_runner/config.py — BootyConfigV1, architect/security field patterns

### Secondary (MEDIUM confidence)
- .planning/phases/37-skeleton-check-plumbing/37-CONTEXT.md — decisions
- docs/reviewer.md — config block spec

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all patterns in codebase
- Architecture: HIGH — mirrors existing agents
- Pitfalls: HIGH — documented from Architect/Verifier phases

**Research date:** 2026-02-17
**Valid until:** 30 days (stable domain)
