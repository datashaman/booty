# Deploy Setup

Configure the deploy workflow and server for automated deployments from GitHub Actions.

## GitHub Environment

1. Go to **GitHub** → **Settings** → **Environments** → **New environment**
2. Name it `production`
3. Add these to the production environment:

### Required

| Variable/Secret | Type | Description |
|-----------------|------|-------------|
| `SSH_PRIVATE_KEY` | Secret | Same key for both: in deploy host `authorized_keys` (runner→server) and repo [deploy key](https://docs.github.com/en/developers/overview/managing-deploy-keys) (clone via agent forwarding) |
| `DEPLOY_HOST` | Variable or Secret | SSH host (IP or hostname) |
| `SERVER_NAME` | Variable | Public hostname (e.g. booty.datashaman.com) |
| `REPO_URL` | Variable | Git clone URL (e.g. <git@github.com>:org/repo.git) |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `DEPLOY_PORT` | 22 | SSH port |
| `DEPLOY_USER` | *(from runner)* | SSH user |
| `HEALTH_SCHEME` | https | `http` or `https` — use https with Cloudflare/Certbot |

## GitHub deploy key (required for private repos)

The deploy script uses SSH agent forwarding: the runner's key is forwarded to the deploy server for `git clone`/`git pull`. Use the **same** key for:

1. **Deploy host** — Add the public key to `~/.ssh/authorized_keys` on the server
2. **GitHub** — Repo → Settings → Deploy keys → Add deploy key (read-only is enough)


## Firewall (required for SSH)

GitHub Actions runners use dynamic IPs. Your server must allow SSH from GitHub's IP ranges:

```bash
# Fetch Actions IP ranges (CIDR)
curl -s https://api.github.com/meta | jq -r '.actions[]'
```

Add these CIDR blocks to your firewall:

- **DigitalOcean**: Networking → Firewalls → Inbound rules for SSH (port 22)
- **ufw**: `ufw allow from <cidr> to any port 22` for each CIDR
- Or your cloud provider's security group / firewall

Without this, the deploy will fail with "SSH connection failed" or timeout.

## Verification

1. Push to `main` with a deploy-relevant change (e.g. `src/`, `deploy.sh`)
2. Check **GitHub Actions** → **Deploy** workflow
3. Workflow runs: preflight → checkout → paths-filter → ssh-agent → Test SSH → Deploy → Health check
