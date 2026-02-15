---
phase: 08-pull-request-webhook-verifier-runner
plan: 01
subsystem: verifier
tags: github-checks, verifier, pytest, asyncio

provides:
  - VerifierJob dataclass with PR context
  - prepare_verification_workspace clones repo at head_sha
  - process_verifier_job runs tests and posts booty/verifier check (queued → in_progress → completed)

key-files:
  created:
    - src/booty/verifier/__init__.py
    - src/booty/verifier/job.py
    - src/booty/verifier/workspace.py
    - src/booty/verifier/runner.py

key-decisions:
  - "Added optional head_ref to prepare_verification_workspace for reliable shallow clone of PR branch"

completed: 2026-02-15
---

# Phase 08 Plan 01: Verifier Runner Summary

**Verifier runner with VerifierJob, prepare_verification_workspace, and process_verifier_job — clones PR head, runs execute_tests, transitions booty/verifier check run queued → in_progress → completed**

## Accomplishments

- VerifierJob dataclass with job_id, owner, repo_name, pr_number, head_sha, head_ref, repo_url, installation_id, payload, is_agent_pr
- prepare_verification_workspace clones repo into temp dir, fetches and checkouts head_sha
- process_verifier_job creates check run, clones workspace, loads .booty.yml, runs execute_tests, updates check to completed (success/failure)

## Task Commits

1. **Task 1: Create VerifierJob and prepare_verification_workspace** — `61fc144` (feat)
2. **Task 2: Create process_verifier_job with check lifecycle** — `ebde5b8` (feat)

## Files Created/Modified

- `src/booty/verifier/__init__.py` — Exports VerifierJob, prepare_verification_workspace
- `src/booty/verifier/job.py` — VerifierJob dataclass
- `src/booty/verifier/workspace.py` — prepare_verification_workspace context manager
- `src/booty/verifier/runner.py` — process_verifier_job async function

## Deviations from Plan

- Added optional `head_ref` parameter to prepare_verification_workspace for reliable shallow clone when checking out PR branch head

## Issues Encountered

None

---
*Phase: 08-pull-request-webhook-verifier-runner*
*Completed: 2026-02-15*
