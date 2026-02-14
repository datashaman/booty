---
phase: 03
plan: 02
subsystem: github-integration
tags: [github, pull-requests, issue-comments, failure-handling]

requires:
  - phase: 02
    plan: 03
    provides: github.pulls module
  - phase: 02
    plan: 05
    provides: pipeline orchestration

provides:
  - Draft PR creation capability
  - Issue comment failure notifications
  - Failure scenario handling infrastructure

affects:
  - phase: 03
    plan: 04
    impact: Will use draft PR and issue comment features for retry logic

tech-stack:
  added:
    - PyGithub issue comment API
  patterns:
    - Draft PR for failed builds pattern
    - Issue comment notification pattern
    - Shared URL parsing helper (_get_repo)

key-files:
  created:
    - src/booty/github/comments.py
  modified:
    - src/booty/github/pulls.py

decisions:
  - name: Draft parameter defaults to False
    rationale: Backward compatibility - existing callers continue creating ready-for-review PRs
    impact: Passing builds create normal PRs, failed builds create drafts
    alternatives: Could have defaulted to True and required explicit ready-for-review flag

  - name: Shared _get_repo helper in comments.py
    rationale: Avoid duplicating URL parsing and auth logic across functions
    impact: Cleaner code, single source of truth for repo access
    alternatives: Could have inlined in each function (DRY violation)

  - name: Formatted markdown for failure comments
    rationale: Clear visual structure improves readability in GitHub UI
    impact: Users get well-formatted error details with context
    alternatives: Plain text (harder to scan), JSON (not human-friendly)

metrics:
  duration: 1.6 min
  completed: 2026-02-14
---

# Phase 03 Plan 02: Draft PR and Issue Comment Support Summary

**One-liner:** Added draft PR parameter and issue comment notifications for build failure scenarios

## What Was Built

Extended GitHub integration with two new capabilities:

1. **Draft PR Support**: Modified `create_pull_request()` to accept `draft` parameter
2. **Failure Comments**: New `post_failure_comment()` function for issue notifications

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add draft PR support to pulls.py | 35152d2 | src/booty/github/pulls.py |
| 2 | Create issue comment module | 7e23f45 | src/booty/github/comments.py |

## Technical Implementation

### Draft PR Support

Modified `create_pull_request()` in `src/booty/github/pulls.py`:
- Added `draft: bool = False` parameter
- Passed `draft=draft` to PyGithub's `repo.create_pull()`
- Enhanced logging to include draft status
- Updated docstring

**Backward compatible**: Existing callers unaffected (defaults to False).

### Issue Comment Notifications

Created `src/booty/github/comments.py` with:
- `_get_repo()` helper: Shared URL parsing and authentication logic
- `post_failure_comment()`: Posts formatted markdown comment with:
  - Attempt count (e.g., "After 3/3 attempts")
  - Error details in code block
  - Note about draft PR for manual review
  - Booty signature link

**Pattern**: Follows same import/auth pattern as pulls.py for consistency.

## Deviations from Plan

None - plan executed exactly as written.

## Key Learnings

**PyGithub API simplicity**: The `draft` parameter is a simple pass-through to PyGithub's `create_pull()` method - no additional validation or logic needed.

**Markdown formatting matters**: Structured markdown (headers, code blocks) significantly improves comment readability in GitHub UI compared to plain text.

**Helper extraction value**: The `_get_repo()` helper eliminated code duplication and provides a clean extension point for future functions needing repo access.

## Integration Points

**Upstream dependencies:**
- PyGithub's `repo.create_pull()` for draft PR creation
- PyGithub's `issue.create_comment()` for failure notifications

**Downstream consumers (planned):**
- Plan 03-04: Retry logic will call `post_failure_comment()` after max retries exceeded
- Plan 03-04: Retry logic will set `draft=True` when creating PR after test failures
- Pipeline orchestrator will conditionally use draft flag based on test results

## Testing Strategy

**Manual verification performed:**
- Import validation for both new functions
- Parameter inspection for `draft` and `error_message`
- No circular imports

**Future integration testing (Plan 03-04):**
- Full retry flow with draft PR creation
- Issue comment posting with real GitHub API
- Error handling for GitHub API failures

## Documentation

**Code documentation:**
- Docstrings updated for `create_pull_request` with draft parameter
- Complete docstrings for `post_failure_comment` and `_get_repo`
- Inline comments for URL parsing logic

**No user-facing docs needed**: Internal API changes only.

## Metrics

- **Duration**: 1.6 minutes
- **Commits**: 2 (one per task)
- **Files created**: 1 (comments.py)
- **Files modified**: 1 (pulls.py)
- **Lines added**: ~100 (95 in comments.py, 9 in pulls.py, -2 refactored)

## Next Phase Readiness

**Status**: Ready for Plan 03-04 (retry logic implementation)

**Provided foundation:**
- Draft PR capability ready for failed builds
- Issue comment notifications ready for failure scenarios
- Backward-compatible API (no breaking changes)

**No blockers identified.**

---
Generated 2026-02-14
