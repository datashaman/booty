# GitHub App Setup for Booty Verifier, Security & Reviewer

The Verifier, Security, and Reviewer agents post check runs via the GitHub Checks API. The Checks API requires **GitHub App** authentication — personal access tokens (PATs) cannot create check runs.

## Required GitHub App Permissions

| Permission | Access | Used for |
|---|---|---|
| **Checks** | Read & write | Create and update check runs (`booty/verifier`, `booty/security`, `booty/reviewer`) |
| **Contents** | Read-only | Read `.booty.yml` config from PR head |
| **Pull requests** | Read-only | Read PR metadata, base/head SHA for Verifier, Security, and Reviewer |
| **Metadata** | Read-only | Repository metadata (auto-granted) |

## Required Webhook Events

Subscribe to these events in the GitHub App settings:

| Event | Purpose |
|---|---|
| **Pull requests** | Triggers Verifier, Security, and Reviewer on `opened`, `synchronize`, `reopened` actions |
| **Issues** | Triggers when labeled `agent` (or opened with it); Planner→Builder (system figures it out) |
| **Workflow runs** | Triggers Release Governor when verification workflow completes on main |
| **Check runs** | Memory PR comment when Verifier check completes; Builder retry on check failure |
| **Push** | Memory revert detection when reverts are pushed to main |

**No new events or permissions needed for Security or Reviewer** — both use the same Pull requests event, Checks API, and Contents API as the Verifier.

## Required `GITHUB_TOKEN` Scopes (PAT)

The Builder and Release Governor use a personal access token (`GITHUB_TOKEN`) for operations the GitHub App doesn't cover:

| Scope | Used for |
|---|---|
| **repo** | Clone repositories, push branches; commit statuses |
| **workflow** | Trigger workflow_dispatch (Release Governor deploy) |
| **pull_requests:write** | Create draft PRs, mark ready for review, request reviewers |
| **issues:write** | Comment on issues/PRs, manage labels; deploy failure issues (Governor) |

The Release Governor additionally needs: `repo` (commit statuses, Contents read for compare/.booty.yml), `workflow` (workflow_dispatch), and `issues:write` (deploy failure issues).

For fine-grained PATs, enable:
- **Contents:** Read and write (clone + push; Governor: read .booty.yml, compare)
- **Pull requests:** Read and write (create PRs, promote drafts)
- **Issues:** Read and write (comments, labels; Governor: deploy failure issues)
- **Actions:** Read and write (Governor: workflow_dispatch deploy)

## Create a New App

1. Go to **GitHub** → **Settings** → **Developer settings** → **GitHub Apps** → **New GitHub App**
2. Fill in:
   - **Name:** e.g. `Booty Verifier`
   - **Homepage URL:** Your repo or docs URL
   - **Webhook URL:** `https://your-domain/webhooks/github`
   - **Webhook secret:** Generate a random secret (same as `WEBHOOK_SECRET` env var)
   - **Permissions** → Repository permissions:
     - Checks: Read and write
     - Pull requests: Read-only
     - Contents: Read-only
     - Metadata: Read-only
   - **Subscribe to events:**
     - Pull requests
     - Issues
     - Workflow runs
     - Check runs
     - Push
3. Create the App
4. Note the **App ID** (visible on the App settings page)
5. Under **Private keys**, click **Generate a private key** — download the `.pem` file

## Use an Existing App

If you already have a GitHub App (e.g. for webhooks):

1. Go to the App settings
2. Note the **App ID**
3. Generate a new private key if needed (or use existing)

## Install the App

1. In your GitHub App settings, click **Install App**
2. Select the **account** or **organization**
3. Choose **All repositories** or **Select repositories**
4. After installing, note the **Installation ID** from the URL:
   `https://github.com/settings/installations/{installation_id}`

## Configure Booty

Set environment variables:

```bash
export GITHUB_APP_ID="123456"  # From App settings → App ID
export GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----"
```

**Private key format:**
- Use the PEM content as-is (with real newlines), or
- Use `\n` in place of newlines when setting in env: `GITHUB_APP_PRIVATE_KEY="-----BEGIN...\n...\n-----END..."`
- Booty normalizes `\\n` to newlines internally

## Verify

Run a test check run:

```bash
booty verifier check-test \
  --repo owner/repo \
  --sha <commit-sha> \
  --installation-id <installation_id>
```

**Example output:**
```
check_run_id=123456789
installation_id=12345
repo=owner/repo
sha=abc123def
status=queued
url=https://github.com/owner/repo/runs/123456789
```

Open the `url` in a browser — the check should appear on the commit in the GitHub UI.

## If Not Configured

When `GITHUB_APP_ID` or `GITHUB_APP_PRIVATE_KEY` is empty:
- **Verifier, Security, and Reviewer are disabled**
- `booty status` shows `verifier: disabled`
- Webhooks accept events but skip check runs
- `booty verifier check-test` exits with error

## GitHub Actions

Security runs **server-side** in Booty when it receives pull_request webhooks — not in GitHub Actions. No workflow changes are needed. Your existing `.github/workflows/*.yml` files are unchanged.

---

*See [README](../README.md) for quick setup, [security-agent.md](security-agent.md) for Security config.*
