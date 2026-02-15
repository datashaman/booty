# Booty

Self-managing builder agent — GitHub issues to tested PRs.

## Running the Server

```bash
uvicorn booty.main:app
```

Set `WEBHOOK_SECRET` and `TARGET_REPO_URL` (and optional `GITHUB_TOKEN`) before starting.

## Verifier (GitHub App)

The Verifier posts check runs (`booty/verifier`) via the GitHub Checks API. It requires GitHub App authentication.

**Quick setup:** Set `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY`. See [docs/github-app-setup.md](docs/github-app-setup.md) for full instructions.

**Verify:**
```bash
booty verifier check-test --repo owner/repo --sha <commit-sha> --installation-id <id>
```

**Status:** `booty status` prints `verifier: enabled` or `verifier: disabled`.
