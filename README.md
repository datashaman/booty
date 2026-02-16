# Booty

Self-managing agent platform — Builder (issues → PRs), Verifier (PR checks), Security (secrets & vulns), Observability (Sentry → issues), and deploy automation.

- **Builder:** Labeled GitHub issues → LLM code generation → test-driven refinement → PRs (including self-modification).
- **Verifier:** Runs on every PR; posts `booty/verifier` check; enforces diff limits, .booty.yml schema, import/compile detection.
- **Security:** Runs on every PR; posts `booty/security` check; secret scan (gitleaks), dependency audit, permission drift → ESCALATE. See [docs/security-agent.md](docs/security-agent.md).
- **Observability:** Sentry webhook → filtered alerts → auto-created GitHub issues with agent:builder.
- **Deploy:** GitHub Actions → SSH → deploy.sh → health check. See [docs/deploy-setup.md](docs/deploy-setup.md).

## Running the Server

```bash
uvicorn booty.main:app
```

Set `WEBHOOK_SECRET`, `TARGET_REPO_URL`, and `GITHUB_TOKEN` before starting.

## Verifier & Security (GitHub App)

The Verifier and Security Agent post check runs (`booty/verifier`, `booty/security`) via the GitHub Checks API. Both require GitHub App authentication.

**Quick setup:** Set `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY`. See [docs/github-app-setup.md](docs/github-app-setup.md) for full instructions. No extra events or permissions are needed for Security — it uses the same pull_request webhook as the Verifier.

**Verify:**
```bash
booty verifier check-test --repo owner/repo --sha <commit-sha> --installation-id <id>
```

**Config:** Add a `security` block to `.booty.yml` in your repo. See [docs/security-agent.md](docs/security-agent.md).

**Status:** `booty status` prints `verifier: enabled` or `verifier: disabled`.
