# Reviewer Agent (v1.9)

AI-driven code quality review on Builder-generated PRs. Sits between Builder and Verifier. Evaluates engineering quality (maintainability, overengineering, duplication, test quality, naming, architectural drift) — not correctness, lint, or security.

## Config (.booty.yml)

```yaml
reviewer:
  enabled: true
  block_on:
    - overengineering
    - poor_tests
    - duplication
    - architectural_regression
```

- **enabled** — When true, Reviewer runs on agent PRs. Default: false (missing block = disabled).
- **block_on** — Categories that trigger BLOCKED when detected. Options: overengineering, poor_tests, duplication, architectural_regression.

Unknown keys in the reviewer block fail Reviewer only; config load continues for other agents.

## Env overrides

- `REVIEWER_ENABLED` — 1/true/yes or 0/false/no. Wins over file config.

## Flow

1. Builder opens PR → Reviewer runs (when enabled for agent PRs)
2. Reviewer analyzes diff via LLM
3. APPROVED → check success, no comment
4. APPROVED_WITH_SUGGESTIONS → check success + comment
5. BLOCKED → check failure + comment; blocks promotion
6. Infra/LLM failure → fail-open (check success, "Reviewer unavailable")

## Check

- **context:** booty/reviewer
- **States:** queued → in_progress → success | failure
- Builder promotion requires booty/reviewer success for agent PRs.

## Comment format

Single updatable comment with marker `<!-- booty-reviewer -->`:

```markdown
## Reviewer — Code Quality

**Decision:** BLOCKED | APPROVED_WITH_SUGGESTIONS

### Findings
- ...

### Recommended Fix
Actionable guidance with file/path references.
```

## Fail-open

When diff fetch, GitHub API, LLM, or schema fails: check success with title "Reviewer unavailable (fail-open)", summary "Review did not run; promotion/merge not blocked". No PR comment. Increments reviewer_fail_open. Failure buckets: diff_fetch_failed, github_api_failed, llm_timeout, llm_error, schema_parse_failed, unexpected_exception.

## Metrics

Persisted under `~/.booty/state/reviewer/metrics.json`: reviews_total, reviews_blocked, reviews_suggestions, reviewer_fail_open (rolling 24h).

## CLI

`booty reviewer status [--repo owner/repo] [--json]`

## Troubleshooting

- **Token missing** — Set GITHUB_TOKEN in environment.
- **Diff fetch** — Ensure base/head SHA are accessible to the GitHub App.
- **LLM timeout** — Increase timeout or check provider availability.
