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



## Test Generation Requirements

Generate unit tests alongside code changes following these repository conventions:

**Language:** python
**Test Framework:** pytest
**Test Directory:** tests/
**Test File Naming:** test_*.py

**CRITICAL:** Use ONLY imports that exist in the project dependencies.
DO NOT hallucinate package names or import paths.
Verify all test imports match the detected framework and project structure.
Check pyproject.toml, package.json, or other config files for available dependencies.

**Example Test Files (for reference):**
- /tmp/booty-20-1mpu3ywm/tests/test_sentry_integration.py
- /tmp/booty-20-1mpu3ywm/tests/test_booty_config.py

Requirements:
1. Generate COMPLETE file contents (not diffs or patches)
2. For new files, provide full content from scratch
3. For modifications, provide the entire updated file with all changes applied
4. For deletions, set operation="delete" and content="" (empty string)
5. Follow the existing code style and conventions visible in the provided files
6. Ensure all imports are present and correct
7. Include clear explanations of what changed and why

Test Generation (when test conventions are provided above):
- Generate unit test files for all changed source files
- Place test files in the `test_files` array, NOT in the `changes` array
- Follow the repository test conventions described above
- Use ONLY imports that exist in the project dependencies - DO NOT hallucinate package names
- Each test file should cover happy path and basic edge cases

CRITICAL: Return the FULL file content, not a diff. The content field should contain the complete file as it should exist after the changes.
