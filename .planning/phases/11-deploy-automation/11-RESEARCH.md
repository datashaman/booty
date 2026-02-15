# Phase 11: Deploy Automation - Research

**Researched:** 2026-02-15
**Domain:** GitHub Actions, SSH deploy to DigitalOcean, deploy.sh integration
**Confidence:** HIGH

## Summary

Phase 11 automates deployment via GitHub Actions: when code is pushed to main (or when a verifier workflow completes successfully on main), the deploy workflow SSHs to DigitalOcean, runs the existing deploy.sh, and restarts Booty. The workflow must support early-exit when no deploy-relevant files changed, use webfactory/ssh-agent for SSH key injection, run health checks post-deploy, and report failures with rich job summaries. All deploy parameters come from GitHub secrets/variables; the workflow file stays minimal.

**Primary recommendation:** Use `webfactory/ssh-agent@v0.9.1` for SSH key setup, `actions/checkout@v4` with `fetch-depth: 0` for change detection, and a shell loop for health checks (max 10 attempts, 6s interval). Trigger on `workflow_run` when verifier completes on main, or `push` to main per REQUIREMENTS. Use `dorny/paths-filter@v3` for deploy_paths filtering when `base` matches the push branch.

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| webfactory/ssh-agent | v0.9.1 | Load SSH private key into ssh-agent | Widely used (1.4k+ stars), no key on disk, supports SSH from Actions runner |
| actions/checkout | v4 | Checkout repo for deploy.sh + change detection | Official, required for git operations |
| dorny/paths-filter | v3 | Detect changed files vs deploy_paths | Used by Sentry, Chrome; supports push + base for main branch |
| Bash (built-in) | — | Preflight env checks, deploy.sh invoker, health check loop | No extra actions; CONTEXT mandates deploy.sh |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| GitHub Environments | production | Secrets scoping; enables future approval gates |
| $GITHUB_STEP_SUMMARY | Job summary | Failure reporting with classification |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| webfactory/ssh-agent | appleboy/ssh-action | appleboy runs commands directly; deploy.sh needs full shell—use webfactory + native ssh |
| dorny/paths-filter | tj-actions/changed-files | dorny has better long-lived-branch support for push to main |
| workflow_run | push to main | REQUIREMENTS say push; CONTEXT prefers workflow_run for verifier chain—support both or use push for v1.3 |

## Architecture Patterns

### Recommended Workflow Structure

```
.github/workflows/deploy.yml
├── on: workflow_run (Verifier) OR push (main)
├── job: deploy
│   ├── Preflight (env vars, fail fast)
│   ├── Checkout (fetch-depth for merge-base)
│   ├── [Optional] paths-filter → exit 0 if no deploy_paths
│   ├── ssh-agent setup
│   ├── Run deploy.sh
│   ├── Health check loop
│   └── Job summary on failure
```

### Pattern 1: workflow_run with conclusion check

**What:** Trigger deploy only when upstream workflow succeeds.
**When:** Verifier runs as GitHub Actions workflow.
**Example:**

```yaml
# Source: GitHub Docs - workflow_run
on:
  workflow_run:
    workflows: [Verifier]
    types: [completed]
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'success'
    steps: ...
```

### Pattern 2: Preflight env validation

**What:** Fail before any remote work if required vars missing.
**Example:**

```bash
: "${DEPLOY_HOST:?Missing DEPLOY_HOST}"
: "${SERVER_NAME:?Missing SERVER_NAME}"
: "${REPO_URL:?Missing REPO_URL}"
```

### Pattern 3: Health check with retries

**What:** Bounded probe (10 attempts, 6s interval) after deploy.
**Example:**

```bash
HEALTH_URL="https://${SERVER_NAME}/health"
for i in $(seq 1 10); do
  if curl -sf "$HEALTH_URL" > /dev/null; then
    echo "runtime_ready=true" >> $GITHUB_OUTPUT
    exit 0
  fi
  sleep 6
done
echo "Deploy failed — health check timeout"
exit 1
```

### Anti-Patterns to Avoid

- **Inline SSH key in workflow:** Never. Use webfactory/ssh-agent with secret.
- **Auto-retry on deploy failure:** CONTEXT forbids; hides infra issues.
- **Skipping health check:** "Deploy success = artifact + service healthy."
- **Using GITHUB_SHA from wrong event:** workflow_run has different SHA semantics; use `github.event.workflow_run.head_sha` when available.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSH key injection | Writing key to temp file | webfactory/ssh-agent | Key never touches disk; agent forwards to ssh |
| Changed-files logic | Custom git diff parsing | dorny/paths-filter | Handles push/PR, merge-base, long-lived branches |
| Health probe | Custom HTTP client | curl in loop | Simple, available on runners |

## Common Pitfalls

### Pitfall 1: workflow_run uses default branch ref

**What goes wrong:** `GITHUB_SHA` in workflow_run is the default branch's last commit, not the workflow that triggered.
**Why:** GitHub Docs state workflow_run provides default branch context.
**How to avoid:** Use `github.event.workflow_run.head_sha` (or `head_commit.id`) when deploying from workflow_run; use `GITHUB_SHA` for push.
**Warning signs:** Deploying wrong commit when using workflow_run.

### Pitfall 2: paths-filter base for push to main

**What goes wrong:** For push to main, `base: ${{ github.ref }}` compares against previous commit on same branch.
**Why:** dorny/paths-filter "long-lived branch" mode: when base equals triggered branch, changes are vs previous commit.
**How to avoid:** Use `base: ${{ github.ref }}` and `filters` with deploy_paths patterns.
**Warning signs:** Always deploying when no runtime-relevant files changed.

### Pitfall 3: SSH key format

**What goes wrong:** "invalid format" when loading key.
**Why:** Key must be PEM; some keys use OpenSSH format.
**How to avoid:** `ssh-keygen -p -f key -m pem` to convert; ensure no passphrase for Actions.
**Warning signs:** webfactory/ssh-agent fails with format error.

## Code Examples

### webfactory/ssh-agent usage

```yaml
# Source: webfactory/ssh-agent README
- uses: webfactory/ssh-agent@v0.9.1
  with:
    ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}
```

### dorny/paths-filter for deploy paths (push to main)

```yaml
# Source: dorny/paths-filter README - long lived branches
- uses: dorny/paths-filter@v3
  id: deploy_filter
  with:
    base: ${{ github.ref }}
    filters: |
      deploy:
        - 'src/**'
        - 'deploy/**'
        - 'deploy.sh'
        - 'pyproject.toml'
        - '.booty.yml'
        - 'requirements*.txt'
        - 'Dockerfile'
        - 'docker-compose*.yml'
        - '.github/workflows/deploy*.yml'
- name: Skip deploy
  if: steps.deploy_filter.outputs.deploy != 'true'
  run: |
    echo "No deploy-relevant changes" >> $GITHUB_STEP_SUMMARY
    exit 0
```

### deploy.sh invocation with env

```bash
export DEPLOY_HOST DEPLOY_USER REPO_URL SERVER_NAME
./deploy.sh
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Inline SSH in workflow | webfactory/ssh-agent | Key never on disk |
| Manual changed-files script | dorny/paths-filter | Maintained, handles edge cases |
| Deploy = push succeeds | Deploy = artifact + health check | Catches runtime failures |

**Deprecated/outdated:**
- Writing SSH key to file: Security risk; use ssh-agent.

## Open Questions

1. **Verifier as workflow vs Booty service:** CONTEXT says workflow_run when verifier completes. Booty v1.2 Verifier is a service posting check runs, not a GitHub workflow. For v1.3, use `push: branches: [main]` per DEPLOY-01 unless a Verifier workflow exists.
2. **Health URL:** Booty uses nginx reverse proxy; health at `https://${SERVER_NAME}/health`. SERVER_NAME defaults to booty.datashaman.com.

## Sources

### Primary (HIGH confidence)

- GitHub Docs — workflow_run, push events
- webfactory/ssh-agent README — usage, inputs, limitations
- dorny/paths-filter README — filters, base, long-lived branches
- Booty deploy.sh — existing flow, env vars

### Secondary (MEDIUM confidence)

- Booty 11-CONTEXT.md — locked decisions

### Tertiary (LOW confidence)

- WebSearch summaries for ecosystem patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — webfactory, dorny widely used; deploy.sh verified
- Architecture: HIGH — Context7 + official docs
- Pitfalls: MEDIUM — some from CONTEXT + docs

**Research date:** 2026-02-15
**Valid until:** 30 days
