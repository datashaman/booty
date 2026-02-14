# Phase 4: Self-Modification - Context

**Gathered:** 2026-02-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable Booty to process issues against its own repository with the same pipeline (analyze, generate, test, PR) as external repos, with enhanced safety rails and human approval requirements. Self-modification is opt-in and protected by configurable path restrictions.

</domain>

<decisions>
## Implementation Decisions

### Safety boundaries
- Protected paths defined via explicit allowlist in `.booty.yml` (per-repo configurable, not Booty-only)
- Three tiers of protection: `.github/workflows/` + `.env` + deployment configs (always blocked), core pipeline modules (configurable per-repo), everything else (fair game)
- For Booty's own repo, core pipeline files (orchestrator, webhook handler, etc.) are on the protected list
- If Booty attempts to modify a protected file: hard fail the job, comment on the issue explaining the restriction, no PR created

### Human approval flow
- Self-modification PRs are always created as draft PRs regardless of test results
- Special label added to self-modification PRs (e.g., `self-modification`)
- A configured GitHub username is auto-requested as reviewer on self-PRs (new config setting)
- PR description includes both a safety summary (which files changed, confirming no protected paths touched) and a diff impact analysis (what the changes affect)
- Self-modification is opt-in: disabled by default, must be explicitly enabled in config (`BOOTY_SELF_MODIFY_ENABLED` or equivalent)
- When self-modification is detected but disabled: log the rejection internally AND comment on the issue explaining self-modification is not enabled

### Bootstrap strategy
- Validation via curated test issues in graduated stages: first a trivial change (typo/docstring), then a simple code change (helper function/bug fix)
- Validation is automated via integration test that creates a mock issue and verifies the pipeline produces a valid PR
- Quality gate for self-PRs: run both test suite AND linting/formatting checks (stricter than external repos)

### Self-target detection
- Detection via URL comparison: compare incoming webhook's repo URL against Booty's own repo URL
- Booty's own repo URL configured via environment variable (`BOOTY_OWN_REPO_URL`)
- URL comparison normalizes for HTTPS/SSH variants, trailing `.git`, and case differences — robust matching

### Claude's Discretion
- Exact format of the protected paths allowlist in `.booty.yml`
- Label name for self-modification PRs
- Specific URL normalization implementation
- Integration test structure and mocking approach
- How lint/format checks are configured and run

</decisions>

<specifics>
## Specific Ideas

- The per-repo protected paths in `.booty.yml` makes the safety feature reusable for any repo, not just Booty itself
- URL normalization should handle the common GitHub URL formats: `https://github.com/org/repo.git`, `https://github.com/org/repo`, `git@github.com:org/repo.git`
- The graduated bootstrap (trivial → simple code) gives confidence without risking real damage

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-self-modification*
*Context gathered: 2026-02-14*
