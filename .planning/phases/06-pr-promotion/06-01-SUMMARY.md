---
phase: 06-pr-promotion
plan: 01
subsystem: github
tags: [pygithub, tenacity, graphql, promotion, retry]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: Logging with structlog
  - phase: 02-github-integration
    provides: PyGithub and PR creation patterns
provides:
  - promote_to_ready_for_review with tenacity retry (5xx/network only)
  - post_promotion_failure_comment (neutral, no Booty branding)
affects: [06-02-pipeline-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - tenacity retry with custom predicate (retry 5xx/network, not 4xx)
    - PyGithub mark_ready_for_review (GraphQL mutation)
    - Neutral failure comment (no product branding)

key-files:
  created:
    - src/booty/github/promotion.py
  modified:
    - src/booty/github/comments.py

key-decisions:
  - "Retry only on status is None or status >= 500 (never on 4xx)"
  - "3 attempts total (2 retries), exponential backoff min=2 max=10"
  - "Comment failure: log only, do not re-raise (CONTEXT fallback)"

patterns-established:
  - "Reuse _get_repo from comments for promotion module"
  - "Caller catches promotion exception and posts failure comment"

# Metrics
duration: 5min
completed: 2026-02-15
---

# Phase 06 Plan 01: Promotion Module Summary

**Promotion module with promote_to_ready_for_review and post_promotion_failure_comment**

## Performance

- **Duration:** 5 min
- **Completed:** 2026-02-15
- **Tasks:** 2
- **Files created:** 1
- **Files modified:** 1

## Accomplishments

- Created `promotion.py` with `promote_to_ready_for_review(github_token, repo_url, pr_number)`
- Tenacity retry: 3 attempts, exponential backoff, retry only on 5xx/network (not 4xx)
- Added `post_promotion_failure_comment` to comments.py with neutral body template
- Comment failure logs only, does not re-raise (per CONTEXT)
- Module loads and signatures verified

## Verification

- `promote_to_ready_for_review` exists with correct signature
- `post_promotion_failure_comment` exists with correct signature
- ruff check passes on modified files

---
*Phase: 06-pr-promotion | Plan: 01 | Completed: 2026-02-15*
