# Dogfooding: Booty Managing Booty

This repo is managed by Booty. Add the `agent` label to an issue to trigger the Planner→Architect→Builder pipeline.

## Config

For Booty to work on itself, set these in `.env` (or server secrets):

```
TARGET_REPO_URL=https://github.com/datashaman/booty
BOOTY_OWN_REPO_URL=https://github.com/datashaman/booty
BOOTY_SELF_MODIFY_ENABLED=true
BOOTY_SELF_MODIFY_REVIEWER=YOUR_GITHUB_USERNAME
```

Plus required: `WEBHOOK_SECRET`, `GITHUB_TOKEN`, `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY` (for Verifier, Security, Reviewer checks).

## Labels

Create these labels (Booty will create them on first use, but pre-creating ensures consistent colors/descriptions):

```bash
./scripts/create-dogfood-labels.sh
```

Or via GitHub API (if `gh label` is unavailable):

```bash
REPO=datashaman/booty
gh api "repos/${REPO}/labels" -X POST -f name="agent" -f description="Triggers Booty Planner→Builder pipeline" -f color="0366d6"
gh api "repos/${REPO}/labels" -X POST -f name="agent:architect-review" -f description="Architect review required" -f color="0366d6"
gh api "repos/${REPO}/labels" -X POST -f name="self-modification" -f description="PR modifies Booty itself" -f color="d93f0b"
```

## Memory: "security_block" in related history

When a PR touches sensitive paths (e.g. `.github/workflows/**`), Security **ESCALATE**s — the check **passes** (conclusion=success) but Memory stores a `security_block` record for related history. The PR comment "Memory: related history" surfaces this. It is informational, not a failure. Governor uses it for deploy risk (HIGH when override present).
## Verify PR Workflow

The `verify-pr.yml` workflow is **disabled** so only Booty agents run verification:

- **Booty Verifier** posts the `booty/verifier` check (tests, limits, import validation)
- **Booty Security** posts the `booty/security` check
- **Booty Reviewer** posts the `booty/reviewer` check when enabled

Duplicate Actions-based verification is avoided. To re-enable for local development, remove the `if: false` in `.github/workflows/verify-pr.yml`.

## Flow

1. Open an issue or add `agent` to an existing one
2. Planner produces a plan → Architect validates (when enabled) → Builder executes
3. Builder opens a draft PR; Verifier runs tests; promotion when all checks pass
4. Self-modification PRs request your review (`BOOTY_SELF_MODIFY_REVIEWER`)
