# Release Governor

Gates production deployment based on risk and approval. Runs when Booty verification completes on main, computes risk from the diff, and either allows deploy (workflow_dispatch) or holds with a clear reason.

When the [Security Agent](security-agent.md) detects sensitive path changes, it persists an override; the Governor reads this and uses `risk_class=HIGH` before computing path-based risk.

## Overview

The Release Governor sits between verification (tests pass on main) and deploy. It:

- Computes **risk** (LOW/MEDIUM/HIGH) from paths touched vs production
- Applies **decision rules** — hard holds, cooldown, rate limit, approval policy
- On **ALLOW**: triggers the deploy workflow via `workflow_dispatch` with exact SHA
- On **HOLD**: posts commit status (or issue) with reason and unblock instructions

Operators can use the CLI to simulate decisions and manually trigger deploys when allowed.

## Execution flow

1. **Push to main** → Booty receives `push` webhook
2. Booty enqueues main verification job; clones main at `head_sha`, runs tests (setup, install, test from `.booty.yml`)
3. On **test success**: Governor evaluates; loads release state; gets `production_sha` (current or previous)
4. Fetches diff: `gh.compare(production_sha, head_sha)`
5. Computes risk from pathspecs (workflows, migrations = HIGH; manifests = MEDIUM; rest = LOW)
6. On **test failure**: posts HOLD with `verification_failed`; no deploy
7. Applies decision rules (when tests passed):
   - **Hard holds**: deploy not configured, first deploy without approval, degraded + HIGH risk
   - **Cooldown**: same SHA failed recently
   - **Rate limit**: max deploys per hour
   - **LOW**: auto-ALLOW
   - **MEDIUM**: ALLOW (unless degraded)
   - **HIGH**: HOLD unless approved (env/label/comment)
8. On **ALLOW**: POST `workflow_dispatch` with `sha` input; update release state
9. On **HOLD**: commit status with Decision, SHA, Risk, Reason, "How to unblock"

## CLI reference

### booty governor status

Show release state.

```bash
booty governor status
booty governor status --json
```

| Option | Description |
|--------|-------------|
| `--workspace PATH` | Workspace dir (default: `.`) |
| `--json` | Machine-readable JSON output |

### booty governor simulate

Dry-run decision for a SHA. No deploy. Requires `GITHUB_TOKEN`.

```bash
booty governor simulate abc123
booty governor simulate --sha abc123 --show-paths
booty governor simulate abc123 --repo owner/repo --json
```

| Option | Description |
|--------|-------------|
| `SHA` | Positional or `--sha` — commit to evaluate |
| `--repo owner/repo` | Override repo (default: infer from git remote) |
| `--workspace PATH` | Workspace dir |
| `--show-paths` | Include paths that drove risk |
| `--json` | Machine-readable JSON output |

**Output (human-readable):**
```
decision: HOLD
risk_class: HIGH
reason: high_risk_no_approval
sha: abc123
unblock: Set RELEASE_GOVERNOR_APPROVED=true
```

### booty governor trigger

Manually trigger deploy when decision is ALLOW. Exits 1 on HOLD. Requires `GITHUB_TOKEN`.

```bash
booty governor trigger abc123
booty governor trigger --sha abc123 --json
```

| Option | Description |
|--------|-------------|
| `SHA` | Positional or `--sha` — commit to deploy |
| `--repo owner/repo` | Override repo |
| `--workspace PATH` | Workspace dir |
| `--json` | Machine-readable JSON output |

On HOLD, prints decision, reason, and unblock hints; exits 1. On ALLOW, dispatches deploy workflow and prints success.

## Configuration

Add a `release_governor` block to `.booty.yml` (schema_version 1):

```yaml
release_governor:
  enabled: true
  production_environment_name: production
  require_approval_for_first_deploy: false
  high_risk_paths:
    - ".github/workflows/**"
    - "**/migrations/**"
  medium_risk_paths:
    - "**/package.json"
    - "**/requirements*.txt"
    - "**/pyproject.toml"
  verification_workflow_name: "Verify main"
  deploy_workflow_name: deploy.yml
  deploy_workflow_ref: main
  cooldown_minutes: 30
  max_deploys_per_hour: 6
  approval_mode: environment
  approval_label: null
  approval_command: null
```

| Field | Default | Description |
|-------|--------|-------------|
| `enabled` | true | Master switch |
| `production_environment_name` | production | GitHub environment name |
| `require_approval_for_first_deploy` | false | Require approval for first-ever deploy |
| `high_risk_paths` | workflows, migrations | Pathspecs for HIGH risk |
| `medium_risk_paths` | manifests (package.json, etc.) | Pathspecs for MEDIUM risk |
| `verification_workflow_name` | "Verify main" | Workflow that triggers Governor |
| `deploy_workflow_name` | deploy.yml | Workflow to dispatch on ALLOW |
| `deploy_workflow_ref` | main | Ref for workflow_dispatch |
| `cooldown_minutes` | 30 | Minutes to wait after deploy failure |
| `max_deploys_per_hour` | 6 | Rate limit |
| `approval_mode` | environment | environment \| label \| comment |
| `approval_label` | null | Label for label mode |
| `approval_command` | null | Comment text for comment mode |

### Environment overrides

`RELEASE_GOVERNOR_*` env vars override config:

| Variable | Maps to |
|----------|---------|
| `RELEASE_GOVERNOR_ENABLED` | enabled |
| `RELEASE_GOVERNOR_APPROVED` | Approval (set to 1/true/yes for environment mode) |
| `RELEASE_GOVERNOR_COOLDOWN_MINUTES` | cooldown_minutes |
| `RELEASE_GOVERNOR_MAX_DEPLOYS_PER_HOUR` | max_deploys_per_hour |
| `RELEASE_GOVERNOR_VERIFICATION_WORKFLOW_NAME` | verification_workflow_name |
| `RELEASE_GOVERNOR_DEPLOY_WORKFLOW_NAME` | deploy_workflow_name |
| `RELEASE_GOVERNOR_PRODUCTION_ENVIRONMENT_NAME` | production_environment_name |
| `RELEASE_GOVERNOR_REQUIRE_APPROVAL_FOR_FIRST_DEPLOY` | require_approval_for_first_deploy |
| `RELEASE_GOVERNOR_APPROVAL_MODE` | approval_mode |
| `RELEASE_GOVERNOR_APPROVAL_LABEL` | approval_label |
| `RELEASE_GOVERNOR_APPROVAL_COMMAND` | approval_command |
| `RELEASE_GOVERNOR_MEDIUM_RISK_PATHS` | medium_risk_paths (comma-separated) |

## Approval mechanism

HIGH risk changes require approval before deploy.

| Mode | How to approve |
|------|----------------|
| **environment** | Set `RELEASE_GOVERNOR_APPROVED=true` (or 1, yes) in env |
| **label** | Add the configured label (e.g. `release:approved`) to the PR |
| **comment** | Comment the configured command (e.g. `/approve`) on the PR |

When using the **CLI** (simulate/trigger), only environment approval applies — set `RELEASE_GOVERNOR_APPROVED=true` before running.

For first deploy with `require_approval_for_first_deploy: true`, same rules apply.

## Troubleshooting

### Deploy not triggering after merges

**Flow:** Push to main → Booty receives `push` webhook → Booty runs verification (clone main, run tests) → on success, Governor evaluates → ALLOW triggers deploy via `workflow_dispatch`.

**Check these in order:**

1. **GitHub App: Push subscription**
   - App Settings → Permissions and events → Subscribe to events.
   - Ensure **Push** is checked so Booty receives push webhooks.

2. **Booty main verification completed successfully**
   - Booty clones main at head SHA and runs tests (setup, install, test from `.booty.yml`).
   - Governor only runs when tests pass. If tests fail, commit status shows HOLD with `verification_failed`.
   - Check Booty logs: `main_verify_enqueued_from_push`, `main_verify_governor_processed`.

3. **GITHUB_TOKEN has workflow permission**
   - Governor uses `GITHUB_TOKEN` for `workflow_dispatch`.
   - Classic PAT: must include `workflow` scope.
   - Fine-grained PAT: Repository permissions → **Actions: Read and write**.
   - Missing permission: `create_dispatch` raises; check Sentry/app logs.

4. **Governor enabled**
   - `.booty.yml` must have `release_governor.enabled: true`.
   - If `.booty.yml` load fails (exception), Governor is treated as disabled (logs `reason=governor_disabled`).

5. **Decision is ALLOW, not HOLD**
   - `.github/workflows/**` and similar paths → HIGH risk → HOLD unless approved.
   - Set `RELEASE_GOVERNOR_APPROVED=true` in **Booty server** environment (e.g. `/opt/booty/.env` or `/etc/booty/secrets.env`), then restart: `sudo systemctl restart booty`. Use `true` without quotes. Simulate uses your local env; the server uses its own.
   - Or run `booty governor simulate <sha>` to see decision and reason.

6. **Repos with custom verification workflow**
   - If using a separate verification workflow (not Booty-owned), `verification_workflow_name` must match `workflow_run.name`.
   - Booty-owned flow does not use `verification_workflow_name`.

### How to see what the Governor is doing

| Where | What |
|-------|------|
| **booty governor status** | Release state: `production_sha_current`, `last_deploy_attempt_sha`, `last_deploy_result` |
| **booty governor simulate &lt;sha&gt;** | Dry-run: decision (ALLOW/HOLD), risk_class, reason, unblock hints |
| **Commit status** | On merge commit: `booty/release-governor` (success = ALLOW, failure = HOLD) |
| **Booty logs** | `main_verify_enqueued_from_push`, `main_verify_governor_processed` (outcome, reason) |
| **Sentry** | `dispatch_deploy` or webhook errors (403 workflow, etc.) |
| **GitHub Actions** | Deploy workflow (only runs when Governor dispatches) |

**Quick diagnostic:**
```bash
# Simulate the latest merge commit
booty governor simulate $(git rev-parse HEAD) --repo datashaman/booty

# Check release state
booty governor status --json
```

### Common hold reasons

| Reason | Cause | Unblock |
|--------|-------|--------|
| `deploy_not_configured` | deploy_workflow_name empty or missing | Add deploy_workflow_name in .booty.yml |
| `first_deploy_required` | First deploy and approval required | Set RELEASE_GOVERNOR_APPROVED=true or use label/comment |
| `high_risk_no_approval` | HIGH risk, no approval | Approve per approval_mode (env/label/comment) |
| `cooldown` | Same SHA failed recently | Wait cooldown_minutes |
| `rate_limit` | Too many deploys in last hour | Wait until deploy count resets |
| `verification_failed` | Tests failed on main | Fix tests and push |
| `degraded_high_risk` | Degraded state + HIGH risk | Fix degraded; or wait |

### Where to look

- **Release state**: `~/.booty/state/release.json` (or `RELEASE_GOVERNOR_STATE_DIR`)
- **Commit status**: On the commit, Booty Governor check shows HOLD/ALLOW and reason
- **Logs**: GitHub Actions workflow logs for the verification and Governor handler

### CLI: GITHUB_TOKEN required

If `booty governor simulate` or `trigger` fails with:
```
GITHUB_TOKEN required for simulate; set it to fetch diff
```
Set the token: `export GITHUB_TOKEN=ghp_...` or ensure it’s in your environment.

## Manual test steps

1. **Status** (Governor enabled):
   ```bash
   booty governor status
   booty governor status --json
   ```

2. **Simulate** a LOW-risk SHA (e.g. docs change):
   ```bash
   booty governor simulate <sha> --repo owner/repo
   # Expect: decision: ALLOW, risk_class: LOW
   ```

3. **Simulate** a HIGH-risk SHA (e.g. workflow change):
   ```bash
   booty governor simulate <sha> --repo owner/repo
   # Expect: decision: HOLD, reason: high_risk_no_approval
   ```

4. **Simulate with approval**:
   ```bash
   RELEASE_GOVERNOR_APPROVED=true booty governor simulate <sha> --repo owner/repo
   # Expect: decision: ALLOW (for HIGH risk)
   ```

5. **Trigger** when ALLOW:
   ```bash
   RELEASE_GOVERNOR_APPROVED=true booty governor trigger <sha> --repo owner/repo
   # Expect: "Triggered: deploy workflow dispatched"
   # Verify: GitHub Actions → Deploy workflow ran
   ```

6. **Trigger** when HOLD (should exit 1):
   ```bash
   booty governor trigger <sha> --repo owner/repo
   # Expect: decision: HOLD, unblock hints; exit code 1
   ```
