---
phase: 12-sentry-apm
plan: 01
subsystem: infra
tags: [sentry, fastapi, error-tracking, apm]

requires: []
provides:
  - Sentry SDK integration at app startup
  - FastAPI/Starlette integrations for unhandled exception capture
  - Release (git SHA) and environment from deploy
  - Production fails startup without DSN
affects: [12-02, 13-observability-agent]

tech-stack:
  added: [sentry-sdk]
  patterns: [init-at-startup, conditional-telemetry, release-correlation]

key-files:
  created: []
  modified: [pyproject.toml, src/booty/config.py, src/booty/main.py, deploy.sh, deploy/booty.service]

key-decisions:
  - "Release omitted when SENTRY_RELEASE empty (never placeholder)"
  - "DSN in secrets.env; release/env in release.env; deploy writes release.env only"

patterns-established:
  - "Sentry init in lifespan before job queue; production+no DSN exits"

duration: 15min
completed: 2026-02-15
---

# Phase 12 Plan 01: Sentry SDK Integration — Summary

**Sentry SDK integrated with FastAPI; init at startup with release/env from deploy; production refuses to start without DSN**

## Performance

- **Duration:** 15 min
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- sentry-sdk dependency and Sentry settings (DSN, release, environment, sample_rate)
- _init_sentry() in lifespan with conditional init: production+no DSN → sys.exit(1); non-prod → skip with log
- Deploy writes /etc/booty/release.env with SENTRY_RELEASE and SENTRY_ENVIRONMENT
- Systemd loads secrets.env (DSN, optional) and release.env (release, env)

## Task Commits

1. **Task 1: Add sentry-sdk and Settings** - `6a11c74` (feat)
2. **Task 2: Sentry init in lifespan** - `15be571` (feat)
3. **Task 3: Deploy writes release.env, systemd loads it** - `e0704d9` (feat)

## Files Created/Modified
- `pyproject.toml` - sentry-sdk dependency
- `src/booty/config.py` - SENTRY_DSN, SENTRY_RELEASE, SENTRY_ENVIRONMENT, SENTRY_SAMPLE_RATE
- `src/booty/main.py` - _init_sentry(), lifespan init
- `deploy.sh` - mkdir /etc/booty, write release.env before restart
- `deploy/booty.service` - EnvironmentFile for secrets.env and release.env

## Decisions Made
None - followed plan as specified

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
- Create Sentry project (Python/FastAPI)
- Add SENTRY_DSN to /etc/booty/secrets.env on deploy host (deploy does NOT write this)
- Local dev: DSN optional; production: DSN required

## Next Phase Readiness
- Plan 12-02 can add capture_exception in process_job and verifier runner
- Unhandled FastAPI exceptions now captured by SDK integrations

---
*Phase: 12-sentry-apm*
*Completed: 2026-02-15*
