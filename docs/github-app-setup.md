# GitHub App Setup for Booty Verifier

The Verifier posts check runs via the GitHub Checks API. The Checks API requires **GitHub App** authentication — personal access tokens (PATs) cannot create check runs.

## Required Permissions

- **checks: write** — Create and update check runs
- **pull_requests: read** — Read PR metadata (Phase 8)
- **contents: read** — Clone repository (Phase 8)
- **metadata: read** — Repository metadata

## Create a New App

1. Go to **GitHub** → **Settings** → **Developer settings** → **GitHub Apps** → **New GitHub App**
2. Fill in:
   - **Name:** e.g. `Booty Verifier`
   - **Homepage URL:** Your repo or docs URL
   - **Webhook:** Uncheck (or set for Phase 8)
   - **Permissions** → Repository permissions:
     - Checks: Read and write
     - Pull requests: Read-only
     - Contents: Read-only
     - Metadata: Read-only
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
- **Verifier is disabled**
- `booty status` shows `verifier: disabled`
- Webhooks accept events but skip check runs
- `booty verifier check-test` exits with error

---

*See [README](../README.md) for quick setup.*
