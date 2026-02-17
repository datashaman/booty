# Viewing Check Results

## GitHub Actions (visible logs)

- **Deploy** — Triggered by Release Governor via `workflow_dispatch` after main verification passes.

PR and main verification are Booty-owned: Verifier, Security, and Reviewer run on the Booty server. Main verification runs on push to main.

## Booty App checks (booty/security, booty/verifier)

These run on the Booty server when a PR is opened or updated. Results appear in the PR **Checks** section.

To see the output:
1. Open the PR
2. Scroll to the checks at the bottom (or click "Checks" in the header)
3. Click the check name (e.g. **booty/security**)
4. The summary/title and error message are shown on the run page

Or via CLI:
```bash
gh pr checks 26
gh api repos/datashaman/booty/commits/HEAD/check-runs | jq '.check_runs[] | {name, conclusion, summary: .output.summary}'
```

## Local runs

```bash
# Run verifier (tests) locally
booty verifier run --workspace .

# Or run pytest directly
pytest tests/ -v
```
