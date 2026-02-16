# Phase 25: Surfacing - Research

**Researched:** 2026-02-16
**Domain:** Memory surfacing into PR comments, Governor HOLD, Observability incident issues
**Confidence:** HIGH

## Summary

Phase 25 surfaces memory context at three integration points: Builder PR comment, Governor HOLD details, and Observability incident issue body. All are informational only (MEM-23). The work is primarily integration of the existing `memory.lookup.query` API into established patterns already used by Verifier (find-or-edit PR comment) and Observability (issue body construction).

No new libraries required. PyGithub (already in use), the memory lookup API (Phase 24), and memory config (Phase 22) provide the full stack. Key research areas: check_run webhook structure for PR-triggered surfacing, GitHub API to find PR for a commit (Governor path), and precise body-insertion points for Observability.

**Primary recommendation:** Add `post_memory_comment` (find-or-edit by `<!-- booty-memory -->`); add `check_run` webhook branch for Verifier completion; extend Governor HOLD path to find PR and update same comment; extend `build_sentry_issue_body` or caller to inject "Related history" section after Sentry link, before stack trace.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyGithub | (project) | GitHub API for comments, issues, commit→PR lookup | Already used; `repo.get_comments()`, `comment.edit()`, `repo.get_commit(sha).get_pulls()` |
| memory.lookup | (Phase 24) | `query(paths, repo, sha, fingerprint, config, max_matches)` | Deterministic; returns type, timestamp, summary, links, id per match |

### Supporting

| Library | Purpose | When to Use |
|---------|---------|-------------|
| booty.github.comments | `_get_repo`, find-or-edit pattern | All PR comment operations |
| booty.github.issues | `build_sentry_issue_body`, `create_issue_from_sentry_event` | Observability body construction |
| booty.memory.config | `MemoryConfig`, `apply_memory_env_overrides`, `get_memory_config` | Enabled/comment_on_pr/comment_on_incident_issue checks |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| check_run webhook | Poll Verifier queue | check_run is event-driven, no polling |
| repo.get_commit(sha).get_pulls() | Search API | PyGithub `Commit.get_pulls()` is cleaner for commit→PR |

## Architecture Patterns

### Recommended Structure

```
src/booty/
├── github/
│   ├── comments.py     # add post_memory_comment (find-or-edit by <!-- booty-memory -->)
│   └── issues.py       # extend build_sentry_issue_body or add inject helper
├── memory/
│   ├── surfacing.py    # NEW: surface_pr, surface_governor_hold, surface_incident_issue
│   └── lookup.py       # existing query()
├── webhooks.py         # add check_run branch; extend workflow_run (Governor HOLD); extend Observability path
```

### Pattern 1: Find-or-edit PR comment

**What:** Iterate `issue.get_comments()`, find comment containing marker (`<!-- booty-memory -->` or `## Verifier Results`), edit if found else create new.

**When to use:** Single updatable comment per PR.

**Example:** (from `post_verifier_failure_comment`)

```python
for comment in issue.get_comments():
    if "## Verifier Results" in (comment.body or ""):
        comment.edit(body)
        return
issue.create_comment(body)
```

For Memory: marker `<!-- booty-memory -->` in body; title "## Memory: related history".

### Pattern 2: check_run webhook for Verifier completion

**What:** Handle `event_type == "check_run"`, `action == "completed"`. Filter `check_run.name == "booty/verifier"`. Use `check_run.pull_requests` or `head_sha` + `repository` to get PR.

**When to use:** Memory must surface only after Verifier has run (CONTEXT decision).

**Payload structure:**
- `check_run`: `name`, `head_sha`, `status`, `conclusion`, `pull_requests` (array of PR refs)
- `repository`: `full_name`, `html_url`
- `installation`: `id`

**Verifier check name:** `booty/verifier` (from checks.py `create_check_run`).

### Pattern 3: Commit → PR lookup (Governor HOLD)

**What:** When Governor HOLD fires, `head_sha` is on main (verification passed). Find PR(s) containing that commit via `GET /repos/{owner}/{repo}/commits/{sha}/pulls`.

**PyGithub:** `repo.get_commit(sha).get_pulls()` returns list of PullRequest. Use first open/merged PR. If none, skip (CONTEXT: "No PR: skip").

### Pattern 4: Issue body injection (Observability)

**What:** `build_sentry_issue_body` returns markdown parts. Insert "Related history" section after Sentry link, before stack trace.

**Current order in build_sentry_issue_body:** severity/env/release → first/last seen → Sentry link → location → stack trace → breadcrumbs.

**Insert point:** After `if web_url` block, before `culprit`/`location`. CONTEXT: "After Sentry link, before stack trace".

### Anti-Patterns to Avoid

- **Multiple Memory comments per PR:** Use single find-or-edit; marker `<!-- booty-memory -->`.
- **Surfacing when zero matches:** Omit comment/section entirely (CONTEXT: empty state = no surface).
- **Querying when disabled:** Check `comment_on_incident_issue` before lookup for Observability; skip entirely when false.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Commit→PR lookup | Custom search | `repo.get_commit(sha).get_pulls()` | GitHub API; handles merge commits |
| Find-or-edit comment | Custom tracking | Iterate `get_comments()`, match marker | Same pattern as Verifier; no external store |
| Check run identity | Name matching | `check_run.name == "booty/verifier"` | Official check name from checks.py |

## Common Pitfalls

### Pitfall 1: check_run for non-PR commits

**What goes wrong:** `check_run.pull_requests` can be empty for direct pushes to main.

**Why it happens:** Checks run on any push; PR context only when commit is in a PR.

**How to avoid:** For Memory PR comment, only surface when `pull_requests` has at least one PR. If empty, skip (no PR to comment on).

### Pitfall 2: Governor HOLD when PR already closed

**What goes wrong:** Governor holds on main; commit may be from merged PR. `get_pulls()` can return closed PRs.

**Why it happens:** We want to add memory links to the PR that introduced the commit.

**How to avoid:** Include closed/merged PRs in search; use first relevant PR. Or filter by `state="all"` if needed. PyGithub `get_pulls()` default may exclude closed — verify and use appropriate params.

### Pitfall 3: Observability body mutation

**What goes wrong:** Modifying `build_sentry_issue_body` in-place could break other callers.

**How to avoid:** Either add optional `related_history: str | None = None` parameter to `build_sentry_issue_body`, or have Observability webhook caller build body then inject section before `create_issue`. Prefer parameter for clarity.

## Code Examples

### Find-or-edit with HTML marker

```python
MARKER = "<!-- booty-memory -->"
TITLE = "## Memory: related history"

def post_memory_comment(github_token: str, repo_url: str, pr_number: int, body: str) -> None:
    repo = _get_repo(github_token, repo_url)
    issue = repo.get_issue(pr_number)
    full_body = f"{TITLE}\n\n{body}\n\n{MARKER}"
    for comment in issue.get_comments():
        if MARKER in (comment.body or ""):
            comment.edit(full_body)
            return
    issue.create_comment(full_body)
```

### check_run handler sketch

```python
if event_type == "check_run" and payload.get("action") == "completed":
    cr = payload.get("check_run", {})
    if cr.get("name") != "booty/verifier":
        return
    pull_requests = cr.get("pull_requests", [])
    if not pull_requests:
        return  # No PR, skip
    pr_number = pull_requests[0].get("number")  # adjust for payload shape
    # ... get paths from PR, run lookup, post_memory_comment
```

### Commit to PR (Governor)

```python
# repo = gh.get_repo(repo_full_name)
# commit = repo.get_commit(head_sha)
# prs = commit.get_pulls()  # or check PyGithub method name
```

**Note:** PyGithub `Commit` object — verify method. GitHub REST is `GET /repos/{owner}/{repo}/commits/{ref}/pulls`.

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-------------------|--------|
| Per-event comments | Single updatable comment (Verifier pattern) | Cleaner UX |
| Inline config | MemoryConfig.comment_on_pr, comment_on_incident_issue | Explicit toggles |

## Open Questions

1. **PyGithub Commit.get_pulls()** — RESOLVED
   - PyGithub `Commit.get_pulls()` exists and returns PaginatedList of PullRequest
   - Use: `repo.get_commit(sha).get_pulls()`

## Sources

### Primary (HIGH confidence)
- Codebase: `src/booty/github/comments.py` (post_verifier_failure_comment)
- Codebase: `src/booty/github/issues.py` (build_sentry_issue_body)
- Codebase: `src/booty/memory/lookup.py` (query)
- Codebase: `src/booty/github/checks.py` (booty/verifier name)
- Codebase: `src/booty/webhooks.py` (pull_request, workflow_run flows)

### Secondary (MEDIUM confidence)
- WebSearch: GitHub check_run payload, commits/{sha}/pulls API

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components exist in codebase
- Architecture: HIGH — patterns from Verifier and Observability
- Pitfalls: MEDIUM — Governor path edge cases; PyGithub commit→PR exact API

**Research date:** 2026-02-16
**Valid until:** 30 days
