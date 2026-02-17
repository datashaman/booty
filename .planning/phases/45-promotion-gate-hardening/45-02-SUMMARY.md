# 45-02: Architect gate for plan-originated PRs — Summary

**Completed:** 2026-02-17
**Plan:** 45-02

## Deliverables

- `src/booty/verifier/promotion_gates.py`: New module with
  - `is_plan_originated_pr(github_token, repo_url, issue_number)` — checks plan comment `<!-- booty-plan -->` or Architect artifact fallback
  - `architect_approved_for_issue(github_token, repo_url, issue_number, owner, repo, state_dir)` — checks `<!-- booty-architect -->` block for ✓ Approved, disk artifact fallback
  - `_parse_owner_repo(repo_url)` — helper to extract owner/repo from URL

- `src/booty/verifier/runner.py`: Architect gate wired after Reviewer gate
  - `get_architect_config`, `apply_architect_env_overrides`, `ArchitectConfigError` from architect.config
  - If `architect_enabled` and `can_promote` and plan-originated: require `architect_approved_for_issue`
  - Logs `promotion_waiting_architect` when blocked
  - Gate order: Reviewer first, Architect second

- `src/booty/verifier/__init__.py`: Exported `architect_approved_for_issue`, `is_plan_originated_pr`

## Verification

- PROMO-02: Architect gate for plan-originated PRs ✓
- PROMO-03: `rg promote_to_ready_for_review src/` — only promotion.py (def) and runner.py (call) ✓
- Smoke test: `is_plan_originated_pr('x','https://github.com/o/r',None) == False` ✓

## Commits

| Task | Commit |
|------|--------|
| Create promotion_gates.py | f92ee9f |
| Wire Architect gate + export | 5c9e4eb |

## Deviations

None.
