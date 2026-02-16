# Phase 11: User Setup Required

**Generated:** 2026-02-15
**Phase:** 11-deploy-automation
**Status:** Incomplete

Complete these items for the deploy workflow to function. Claude automated the workflow; these items require human access to GitHub settings and your deploy infrastructure.

## Environment Variables / Secrets

| Status | Variable | Source | Add to |
|--------|----------|--------|--------|
| [ ] | `SSH_PRIVATE_KEY` | Private key with SSH access to deploy host | GitHub Settings → Environments → production → Secrets |
| [ ] | `DEPLOY_HOST` | SSH host (IP or hostname) for deploy target | GitHub Settings → Environments → production → Variables or Secrets |
| [ ] | `DEPLOY_PORT` | SSH port (optional; default 22) | GitHub Settings → Environments → production → Variables or Secrets |
| [ ] | `DEPLOY_USER` | SSH user (optional; deploy.sh defaults to `whoami`) | GitHub Settings → Environments → production → Variables or Secrets |
| [ ] | `SERVER_NAME` | Public hostname for health check (e.g. booty.datashaman.com) | GitHub Settings → Environments → production → Variables |
| [ ] | `REPO_URL` | Git clone URL (e.g. git@github.com:org/repo.git) | GitHub Settings → Environments → production → Variables |
| [ ] | `HEALTH_SCHEME` | `http` (default) or `https` — use https if SSL (Certbot, Cloudflare) | GitHub Settings → Environments → production → Variables |

## Dashboard Configuration

- [ ] **Create production Environment**
  - Location: GitHub repo → Settings → Environments → New environment
  - Name: `production`
  - Enables scoping secrets/variables to deploy workflow

- [ ] **Add secrets and variables**
  - Location: Environment `production` → Add secret / Add variable
  - Required secrets: `SSH_PRIVATE_KEY`
  - Required variables: `DEPLOY_HOST`, `SERVER_NAME`, `REPO_URL`
  - Optional: `DEPLOY_PORT` (SSH port; omit for default 22)
  - Optional: `DEPLOY_USER` (deploy.sh defaults to current user if unset)

## Verification

After completing setup:

1. Push to `main` with a deploy-relevant file change (e.g. edit `src/` or `deploy.sh`)
2. Check GitHub Actions → Deploy workflow
3. Workflow should: run preflight → checkout → paths-filter → ssh-agent → deploy.sh → health check

Expected: Job succeeds with green check, Booty service restarted on deploy host.

To test paths-filter (no deploy): Push a change only to `docs/` or `README.md` — workflow should exit early with "No deploy-relevant changes".

---

**Once all items complete:** Mark status as "Complete" at top of file.
