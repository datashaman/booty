# Phase 7: GitHub App + Checks Integration - Research

**Researched:** 2026-02-15
**Domain:** GitHub Checks API, GitHub App authentication, PyGithub
**Confidence:** HIGH

## Summary

Phase 7 unblocks the Checks API by adding GitHub App authentication and a `booty/github/checks.py` module. The Checks API rejects PATs (403); only GitHub App tokens with `checks:write` can create check runs. PyGithub supports `Auth.AppAuth` and `GithubIntegration.get_github_for_installation(installation_id)` — no new libraries needed. Booty keeps PAT for Builder; Verifier path uses App token exclusively for checks.

**Primary recommendation:** Use PyGithub's `GithubIntegration.get_github_for_installation(installation_id)` to obtain a `Github` instance with installation token; call `repo.create_check_run()` on that instance. Add `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY` to Settings (optional when empty — Verifier disabled).

## Standard Stack

### Core (Use These)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyGithub | existing | `Auth.AppAuth`, `GithubIntegration`, `repo.create_check_run()` | Already in stack; full Checks API support |
| pydantic-settings | existing | Settings extension for GITHUB_APP_ID, PRIVATE_KEY | Booty uses BaseSettings; consistent pattern |

### Don't Add

| Avoid | Why |
|-------|-----|
| PyJWT direct | PyGithub's `Auth.AppAuth` handles JWT internally |
| httpx/raw REST for checks | PyGithub has `create_check_run`; no need |
| New auth library | PyGithub supports App auth natively |

## Architecture Patterns

### GitHub App → Installation Token Flow

```python
# Source: PyGithub Authentication examples (Context7)
from github import Auth, Github
from github import GithubIntegration

auth = Auth.AppAuth(app_id=int(settings.GITHUB_APP_ID), private_key=settings.GITHUB_APP_PRIVATE_KEY)
gi = GithubIntegration(auth=auth)
g = gi.get_github_for_installation(installation_id)  # Returns Github with installation token
repo = g.get_repo(f"{owner}/{repo_name}")
check_run = repo.create_check_run(name="booty/verifier", head_sha=sha, status="queued", output={...})
```

### Check Run Lifecycle (per CONTEXT.md)

1. **queued** — Initial creation
2. **in_progress** — `check_run.edit(status="in_progress", ...)`
3. **completed** — `check_run.edit(status="completed", conclusion="success"|"failure", ...)`

### Project Structure

```
src/booty/
├── config.py          # Add GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY (optional)
├── github/
│   ├── checks.py     # NEW: create_check_run, edit_check_run (App auth only)
│   └── ...
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT for App auth | Custom JWT signing | PyGithub `Auth.AppAuth` | Handles expiration, formatting |
| Installation token | Manual REST calls | `GithubIntegration.get_github_for_installation()` | Caching, renewal |
| Check run API | Raw HTTP | `repo.create_check_run()`, `check_run.edit()` | Type-safe, tested |

## Common Pitfalls

### Pitfall 1: PAT for Checks API
**What goes wrong:** Using `Github(auth=Auth.Token(pat))` then `repo.create_check_run()` returns 403 Forbidden.
**Why:** GitHub only allows GitHub App tokens for Checks API write operations.
**How to avoid:** Use `GithubIntegration.get_github_for_installation(installation_id)` for all check run operations.

### Pitfall 2: Missing installation_id
**What goes wrong:** App auth succeeds but `get_github_for_installation()` needs installation ID — webhook provides it; CLI needs `--installation-id` flag.
**How to avoid:** `booty verifier check-test` requires `--installation-id` when not inferrable; document in README.

### Pitfall 3: Private key format
**What goes wrong:** PEM string with literal `\n` instead of newlines; PyGithub/JWT fails.
**How to avoid:** Accept PEM with `\n` in env; replace `\\n` with actual newlines before passing to Auth.AppAuth.

## Code Examples

### Create Check Run (Minimal)

```python
# Source: PyGithub Context7 + GitHub Checks API
check_run = repo.create_check_run(
    name="booty/verifier",
    head_sha=head_sha,
    status="queued",
    output={"title": "Booty Verifier", "summary": "Queued"}
)
# Returns CheckRun with .id, .url, .html_url, .status
```

### Edit Check Run (Lifecycle)

```python
check_run.edit(status="in_progress", output={"title": "...", "summary": "..."})
check_run.edit(status="completed", conclusion="success", output={...})
# conclusion: success | failure | neutral | cancelled | skipped | stale
```

## State of the Art

| Old Approach | Current Approach | Impact |
|-------------|------------------|--------|
| PAT for Checks API | GitHub App only | PAT returns 403; must use App |
| Commit Status API | Checks API | Checks are first-class; required-check support |

## Open Questions

1. **installation_id source for CLI** — User provides via `--installation-id`; can be discovered via `GithubIntegration.get_installations()` but requires JWT (App-level) which has different permissions. Recommendation: require flag for `check-test`.
2. **PEM newline handling** — Some env loaders preserve `\n`; some don't. Recommendation: in Settings validator, normalize PEM (replace `\\n` with `\n` if needed).

## Sources

### Primary (HIGH confidence)
- PyGithub Context7 — Auth.AppAuth, GithubIntegration, create_check_run, CheckRun.edit
- GitHub REST API — Checks runs endpoint, authentication requirements

### Secondary (MEDIUM confidence)
- Web search — "GitHub Checks API requires GitHub App not PAT" (verified: write requires App)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PyGithub and pydantic-settings are existing; Context7 verified
- Architecture: HIGH — Flow documented in PyGithub examples
- Pitfalls: HIGH — GitHub docs and research confirm PAT restriction

**Research date:** 2026-02-15
**Valid until:** 30 days (stable APIs)
