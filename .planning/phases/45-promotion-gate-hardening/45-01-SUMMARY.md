# 45-01: Idempotent promote_to_ready_for_review — Summary

**Completed:** 2026-02-17
**Plan:** 45-01

## Deliverables

- `src/booty/github/promotion.py`: Added idempotency check before `mark_ready_for_review()`
  - Re-fetches PR via `repo.get_pull(pr_number)`
  - If `not pr.draft`: logs `pr_already_ready`, returns without promoting
  - Updated docstring to document idempotent behavior
  - Existing retry decorator and `_should_retry_promotion` unchanged

## Verification

- `grep -n "pr\.draft\|pr_already_ready" promotion.py` — passes
- PROMO-05: promote_to_ready_for_review is idempotent ✓

## Commits

| Task | Commit |
|------|--------|
| Add idempotency to promote_to_ready_for_review | 4b9de93 |

## Deviations

None.
