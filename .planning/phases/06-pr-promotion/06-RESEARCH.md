# Phase 6: PR Promotion - Research

**Researched:** 2026-02-15
**Domain:** GitHub PR promotion (draft → ready-for-review), PyGithub, retry patterns
**Confidence:** HIGH

## Summary

Phase 6 implements automatic promotion of draft PRs to ready-for-review when validation passes. The project already uses PyGithub and has prior research (v1.1 SUMMARY.md, STACK.md) confirming `mark_ready_for_review()` exists. There is **no REST API** for draft→ready conversion — GitHub requires the **GraphQL** `markPullRequestReadyForReview` mutation. PyGithub wraps this.

Key findings: (1) PyGithub's `PullRequest.mark_ready_for_review()` uses GraphQL under the hood; (2) the project already has tenacity for retries; (3) quality checks (ruff) currently run only for self-modification — promotion requires running them for all PRs; (4) PR comments use `issue.create_comment()` (PRs are issues); (5) CONTEXT.md decisions constrain retry (2 retries, 3 attempts; retry 5xx/network, not 4xx), failure comment (neutral, no Booty branding), and self-mod always draft.

**Primary recommendation:** Use PyGithub's `mark_ready_for_review()` with tenacity retry. Always create PRs as draft when promotion candidate; run quality checks for all jobs; promote only when tests+lint pass and not self-mod.

## Standard Stack

The project already uses the required stack. No new dependencies.

### Core

| Library   | Version | Purpose                    | Why Standard                 |
|----------|---------|----------------------------|------------------------------|
| PyGithub | 2.x     | GitHub API, PR promotion   | Already used; has GraphQL    |
| tenacity | (project)| Retry with backoff        | Already used in prompts.py   |

### Promotion Flow

| Step                 | Current                         | Phase 6 Change                              |
|----------------------|----------------------------------|---------------------------------------------|
| Quality checks       | Self-modification only          | Run for ALL jobs (promotion gate)           |
| PR creation          | draft=(not tests_passed) or True| Always draft when promotion candidate       |
| After creation       | None                            | If tests+lint pass, not self-mod → promote  |
| Promotion failure    | N/A                             | Post PR comment, leave draft                |

**Installation:** No new packages. PyGithub and tenacity already in pyproject.toml.

## Architecture Patterns

### Recommended Integration Point

Promotion happens **after** PR creation in `process_issue_to_pr`:

```
... create PR (draft) ...
... add self-mod metadata if needed ...
# NEW: Phase 6
if should_promote(tests_passed, quality_passed, is_self_modification):
    promote_pr_with_retry(...)  # or post_failure_comment on exception
```

### Promotion Logic

```python
# Pseudocode — planner will implement
def should_promote(tests_passed: bool, quality_passed: bool, is_self_modification: bool) -> bool:
    return tests_passed and quality_passed and not is_self_modification
```

### Retry Pattern (tenacity)

CONTEXT: Retry 2 retries (3 attempts total); retry on 5xx, network; do not retry on 4xx.

```python
# Source: project uses tenacity in booty/llm/prompts.py
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# Retry on transient errors (GithubException with 5xx, connection errors)
# Do NOT retry on 4xx (auth, not found)
@retry(
    retry=retry_if_exception_type((GithubException, ConnectionError, TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
def promote_pr(...):
    ...
```

**Caveat:** `GithubException` includes 4xx. Must check `e.status >= 500` or equivalent before retrying. Use custom retry predicate.

### PyGithub Promotion

```python
# Source: Context7, PyGithub PullRequest
# PR has node_id (GraphQL ID). mark_ready_for_review() uses GraphQL mutation.
repo = g.get_repo(owner_repo)
pr = repo.get_pull(pr_number)
pr.mark_ready_for_review()  # Returns dict
```

### PR Comment (Failure Visibility)

```python
# Source: booty/github/comments.py — issue.create_comment for PRs
# PRs are issues; use repo.get_issue(pr_number) or pr.as_issue().create_comment()
pr = repo.get_pull(pr_number)
pr.as_issue().create_comment(body)
```

CONTEXT: Neutral message, no Booty branding. If comment fails → logs only.

### Anti-Patterns to Avoid

- **Don't use REST PATCH for draft:** REST API has no draft→ready endpoint. Must use GraphQL.
- **Don't retry on 4xx:** Auth/not-found won't succeed on retry.
- **Don't skip quality for non-self-mod:** Promotion requires linting clean for all.

## Don't Hand-Roll

| Problem                 | Don't Build             | Use Instead             | Why                         |
|-------------------------|-------------------------|--------------------------|-----------------------------|
| GraphQL mutation        | Raw requests            | PyGithub mark_ready_for_review | Already wraps GraphQL       |
| Retry/backoff           | Manual loops            | tenacity                 | Project standard            |
| PR failure notification | Custom webhook          | issue.create_comment     | Same as post_failure_comment |

## Common Pitfalls

### Pitfall 1: Retrying on 4xx

**What goes wrong:** Retries waste time on auth/404.
**How to avoid:** Use retry_if_exception with custom check: `e.status is None or e.status >= 500`.
**Warning signs:** Many retries, same error.

### Pitfall 2: Quality Checks Only for Self-Mod

**What goes wrong:** Promote PR with lint errors.
**How to avoid:** Run `run_quality_checks` for ALL jobs before promotion decision.
**Warning signs:** Promoted PR fails CI on lint.

### Pitfall 3: Comment Failure Blocking

**What goes wrong:** Promotion failed, comment post fails, whole job fails.
**How to avoid:** Try comment, on exception log only. Do not re-raise.
**Warning signs:** Job fails when only comment failed.

### Pitfall 4: Self-Modification Promotion

**What goes wrong:** Accidentally promote self-mod PR.
**How to avoid:** `should_promote` must explicitly exclude `is_self_modification`.
**Warning signs:** Self-mod PR becomes ready.

## Code Examples

### Promotion with Retry (custom predicate)

```python
def _should_retry_promotion(exc: BaseException) -> bool:
    if isinstance(exc, GithubException):
        return exc.status is None or exc.status >= 500
    return isinstance(exc, (ConnectionError, TimeoutError))

@retry(
    retry=retry_if_exception(_should_retry_promotion),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
def promote_to_ready_for_review(github_token: str, repo_url: str, pr_number: int) -> None:
    ...
    pr = repo.get_pull(pr_number)
    pr.mark_ready_for_review()
```

### Post Promotion Failure Comment

```python
# CONTEXT: Neutral, no Booty branding
body = f"""## Could not promote to ready for review

Promotion was not completed after {attempts} attempt(s).

{reason}

---
PR remains in draft for manual review."""
pr.as_issue().create_comment(body)
```

## State of the Art

| Old Approach          | Current Approach           | Impact                          |
|-----------------------|----------------------------|----------------------------------|
| REST for everything   | GraphQL for draft→ready    | REST has no endpoint             |
| Manual retry loops    | tenacity                   | Consistent, configurable         |
| Quality only self-mod | Quality for all (Phase 6) | Promotion gate requires it       |

**Deprecated/outdated:** None. Stack is current.

## Open Questions

1. **Multi-linter (CONTEXT discretion):** Current quality.py runs ruff only. CONTEXT says "design for multiple linters". For Phase 6 MVP, ruff-only is sufficient; multi-linter can be a follow-up if .booty.yml gains linter config.
2. **Exact tenacity predicate:** `retry_if_exception` vs `retry_if_exception_type` — use custom callable for status check.

## Sources

### Primary (HIGH confidence)

- Context7 /pygithub/pygithub — markPullRequestReadyForReview, create_issue_comment
- Project .planning/research/STACK.md, SUMMARY.md — mark_ready_for_review confirmed
- Project src/booty/github/pulls.py, comments.py — existing patterns
- Project src/booty/llm/prompts.py — tenacity usage

### Secondary (MEDIUM confidence)

- WebSearch — GitHub REST has no draft→ready endpoint; GraphQL required
- PyGithub PullRequest.py (fetched) — enable_automerge uses graphql_named_mutation; mark_ready_for_review likely similar

### Tertiary (LOW confidence)

- WebSearch — PyGithub docs sparse on mark_ready_for_review; project research and Context7 are primary

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PyGithub and tenacity in project, prior v1.1 research
- Architecture: HIGH — clear integration point, existing comment pattern
- Pitfalls: HIGH — standard retry/auth/self-mod gotchas

**Research date:** 2026-02-15
**Valid until:** 2026-03-15 (PyGithub stable)
