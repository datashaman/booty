---
phase: 11-deploy-automation
plan: "01"
subsystem: infra
tags: [github-actions, deploy, ssh, webfactory-ssh-agent, paths-filter]

# Dependency graph
requires: []
provides:
  - Automated deploy workflow (push to main → SSH → deploy.sh → health check)
  - paths-filter early exit when no deploy-relevant changes
  - Structured failure summary on deploy or health check failure
affects: [12-sentry-apm, 13-observability-agent]

# Tech tracking
tech-stack:
  added: [dorny/paths-filter, webfactory/ssh-agent]
  patterns: [GitHub Environments for secrets, deploy-path whitelist]

key-files:
  created: [.github/workflows/deploy.yml]
  modified: []

key-decisions:
  - "Push-to-main trigger (plan choice); 11-CONTEXT suggested workflow_run post-verifier"
  - "vars.DEPLOY_HOST with secrets fallback for flexibility"
  - "Single deploy target (production); staging/rollback deferred"

patterns-established:
  - "Preflight env validation before any remote mutation"
  - "Failure classification: SSH/network, auth, remote script exit, health check timeout"
  - "deploy_transport_success and runtime_ready reported separately on failure"

# Metrics
duration: ~15 min
completed: "2026-02-15"
---

# Phase 11 Plan 01: Deploy Workflow Summary

**GitHub Actions deploy workflow with push-to-main trigger, paths-filter, ssh-agent, deploy.sh invocation, and /health check**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-15
- **Completed:** 2026-02-15
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- `.github/workflows/deploy.yml` created with push-to-main trigger
- Preflight validates DEPLOY_HOST, SERVER_NAME, REPO_URL before any deploy work
- paths-filter (dorny/paths-filter@v3) exits early when no deploy-relevant files changed
- webfactory/ssh-agent loads SSH key; deploy.sh runs with env
- Health check: curl to https://${SERVER_NAME}/health, 10 attempts × 6s
- Failure summary written to GITHUB_STEP_SUMMARY with class, host, stage, exit code, last 20 lines

## Task Commits

1. **Task 1–3: Deploy workflow** — `d016a6b` (feat)

**Plan metadata:** pending (docs commit)

## Files Created/Modified

- `.github/workflows/deploy.yml` — Deploy workflow (trigger, preflight, checkout, paths-filter, ssh-agent, deploy.sh, health check, failure handling)

## Decisions Made

- Used `vars.DEPLOY_HOST || secrets.DEPLOY_HOST` pattern to support both variable and secret sources
- deploy_paths whitelist from 11-CONTEXT: src/**, deploy/**, deploy.sh, pyproject.toml, .booty.yml, requirements*.txt, Dockerfile, docker-compose*.yml, .github/workflows/deploy*.yml
- Health check uses SERVER_NAME (public URL) not DEPLOY_HOST (SSH target)

## Deviations from Plan

None — plan executed as specified.

## Issues Encountered

None

## User Setup Required

**External services require manual configuration.** See [11-USER-SETUP.md](./11-USER-SETUP.md) for:

- GitHub production Environment creation
- SSH_PRIVATE_KEY, DEPLOY_HOST, SERVER_NAME, REPO_URL, DEPLOY_USER (secrets/variables)
- Verification steps

## Next Phase Readiness

- Deploy workflow ready; user must configure GitHub Environment and secrets before first deploy
- Phase 12 (Sentry APM) can proceed independently

---
*Phase: 11-deploy-automation*
*Completed: 2026-02-15*
