# Booty

Self-managing agent platform — Builder (issues → PRs), Verifier (PR checks), Observability (Sentry → issues), and deploy automation.

- **Builder:** Labeled GitHub issues → LLM code generation → test-driven refinement → PRs (including self-modification).
- **Verifier:** Runs on every PR; posts `booty/verifier` check; enforces diff limits, .booty.yml schema, import/compile detection.
- **Observability:** Sentry webhook → filtered alerts → auto-created GitHub issues with agent:builder.
- **Deploy:** GitHub Actions → SSH → deploy.sh → health check. See [docs/deploy-setup.md](docs/deploy-setup.md).

## Running the Server

```bash
uvicorn booty.main:app
```

Set `WEBHOOK_SECRET`, `TARGET_REPO_URL`, and `GITHUB_TOKEN` before starting.

## Verifier (GitHub App)

The Verifier posts check runs (`booty/verifier`) via the GitHub Checks API. It requires GitHub App authentication.

**Quick setup:** Set `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY`. See [docs/github-app-setup.md](docs/github-app-setup.md) for full instructions.

**Verify:**
```bash
booty verifier check-test --repo owner/repo --sha <commit-sha> --installation-id <id>
```

**Status:** `booty status` prints `verifier: enabled` or `verifier: disabled`.
