# Stack Research: Verifier Agent

**Domain:** GitHub Checks API, PR verification, CI gating
**Researched:** 2026-02-15
**Confidence:** HIGH

## Executive Summary

The Verifier agent requires **GitHub App authentication** — the Checks API does not accept PATs or OAuth tokens. Booty currently uses `Auth.Token(github_token)`; we must add GitHub App support for the Verifier path. PyGithub supports both; no library swap required.

## Recommended Stack Additions

### Core Requirement: GitHub App for Checks API

| Technology | Purpose | Why Required |
|------------|---------|--------------|
| **PyGithub Auth.AppAuth** | GitHub App JWT + installation token | Checks API only accepts GitHub App auth; PATs cannot create check runs |
| **GithubIntegration** (PyGithub) | Get installation token per repo | Verifier needs `checks:write`; `repo.create_check_run()` requires App token |

**Critical:** GitHub docs state: "OAuth apps and authenticated users can only view check runs and check suites, but cannot create them." [GitHub REST API]

### Stack Additions (Minimal)

| Addition | Version | Purpose | Integration |
|----------|---------|---------|-------------|
| **PyJWT** | 2.8+ | JWT generation for App auth | PyGithub's `Auth.AppAuth` uses it internally; may already be transitive |
| **None** | — | Diff stats | Use `git diff --stat` or PyGithub PR `changed_files`, `additions`, `deletions` |

### Existing Stack (Reuse)

| Component | Current Use | Verifier Use |
|-----------|-------------|--------------|
| **test_runner/executor** | Builder runs tests in workspace | Verifier clones PR branch, runs same `execute_tests()` in clean env |
| **test_runner/config** | .booty.yml loading | Extend BootyConfig for schema v1 (allowed_paths, forbidden_paths, etc.) |
| **PyGithub** | PR creation, comments | Checks API via `repo.create_check_run()`, `check_run.edit()` |
| **pathspec** | Path restrictions | Diff limit enforcement (max_loc_per_file for safety-critical dirs) |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **PAT for Checks API** | API rejects it — 403/401 | GitHub App with `checks:write` |
| **Commit Status API** | User wanted required check `booty/verifier`; statuses are less first-class | Checks API (requires App) |
| **New test runner** | Builder's `execute_tests()` is proven | Reuse; Verifier = fresh clone + same executor |

## GitHub App Setup (Required)

Booty must be deployed as a **GitHub App** (or run with an App installation token) for Verifier:

1. Create GitHub App with permissions: `checks: write`, `pull_requests: read`, `contents: read`, `metadata: read`
2. Subscribe to `pull_request` (actions: opened, synchronize)
3. Generate installation access token via `GithubIntegration.get_github_for_installation(installation_id)`
4. Use that token for `repo.create_check_run()` calls

**Dual-auth strategy:** Builder can keep PAT (issues, PR creation, comments). Verifier uses App token (Checks API only). Two code paths, one app.

## Alternatives Considered

| Recommended | Alternative | When to Use |
|-------------|-------------|-------------|
| GitHub App | Commit Status API | If user accepts "build failing" status instead of named check — lower setup but less first-class |
| PyGithub | httpx direct to REST | PyGithub has `create_check_run`; no need for raw HTTP |

## Version Compatibility

| PyGithub | Auth.AppAuth | Notes |
|----------|--------------|-------|
| 2.x | Supported | `Auth.AppAuth(app_id, private_key)` |
| — | GithubIntegration | `get_github_for_installation(installation_id)` returns `Github` with App token |

## Sources

- PyGithub Context7 — CheckRun, Auth.AppAuth, GithubIntegration
- GitHub REST API docs — Checks API, authentication
- Web search — "GitHub Checks API requires GitHub App not PAT"

---
*Stack research for: Verifier agent (Booty v1.2)*
*Researched: 2026-02-15*
