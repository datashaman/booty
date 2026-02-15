# Phase 11: Deploy Automation - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Automated deployment via GitHub Actions. Push to main that passes verification triggers SSH to DigitalOcean, runs deploy.sh, restarts Booty. Deploy is a separate workflow that runs only after verifier success; includes health check to confirm runtime viability. Single deploy target (production); staging/rollback are future phases.

</domain>

<decisions>
## Implementation Decisions

### Deploy Script Usage

- **Reuse deploy.sh as-is** — Workflow checks out repo, runs `./deploy.sh`; script SSHs to DO from Actions runner.
- **Parameters via env vars** — All (`DEPLOY_HOST`, `SERVER_NAME`, `REPO_URL`, `DEPLOY_USER`) from secrets/vars before calling deploy.sh.
- **SSH key** — Add private key as GitHub secret; configure via `ssh-agent` or equivalent (e.g. webfactory/ssh-agent). Never inline in workflow.

### Secrets & Config

- **Blast-radius rule** — If exposure creates lateral movement or infra compromise → secret. If exposure only reveals topology → variable.
- **Secrets** (in `production` Environment): `SSH_PRIVATE_KEY`, `DEPLOY_HOST` (if not publicly known), `DEPLOY_USER` (if sensitive).
- **Variables** (repo vars, or Environment vars): `SERVER_NAME`, `REPO_URL`, `DEPLOY_PORT` (if used). Workflow treats vars as source — near-zero deploy data in workflow file.
- **Environment** — Use `production` GitHub Environment. Environments describe where code lands, not how it gets there. Enables approval gates later without workflow redesign.
- **Preflight** — Missing deploy variable = configuration error = stop immediately. Add preflight step before SSH: `: "${SERVER_NAME:?Missing SERVER_NAME}"` etc. Fail before any remote mutation.

### Failure Handling

- **Deploy check** — Native Actions job named `booty/deploy`. One decision surface per boundary (verifier = custom check; deploy = Actions job). Required check on protected branches.
- **No auto-retry** — Failed deploy must never auto-retry. Retries hide infra instability; force operator decision.
- **Rich job summary** — Use `$GITHUB_STEP_SUMMARY` for failure block. Include: failure class, host, user, stage, exit code, last ~20 lines output. Never dump full logs or leak secrets. Classify: SSH/network, auth, remote script exit, checkout failure, health check timeout.
- **Health check required** — Deploy success = artifact landed + service healthy. Bounded probe: max 10 attempts, 6s interval (~60s). Fail with "Deploy failed — health check timeout".
- **Distinguish transport vs runtime** — Report `deploy_transport_success` and `runtime_ready` separately; overall status = failed if either fails.

### Trigger Scope

- **workflow_run trigger** — Deploy runs when verifier workflow completes successfully on main. Use verifier's `head_sha` from payload — never "latest main".
- **Early-exit on no deploy-relevant changes** — First step: checkout `head_sha`, compute changed files vs previous main, if none match `deploy_paths` → exit 0 with summary "No deploy-relevant changes", green check.
- **Deterministic pipeline** — Every verifier-success on main produces a deploy outcome (deployed or no-op). Good for auditing.
- **deploy_paths whitelist** (Booty v1.3): `src/**`, `deploy/**`, `deploy.sh`, `pyproject.toml`, `.booty.yml`, `requirements*.txt`, `Dockerfile`, `docker-compose*.yml`, `.github/workflows/deploy*.yml`. If it can change runtime behavior → deploy. Err on the side of deploying; don't over-tighten until Observability is wired.

### Claude's Discretion

- Exact ssh-agent / SSH setup action choice
- Health check URL (e.g. `/health`) and probe implementation details
- Changed-files computation (merge base vs previous main SHA)

</decisions>

<specifics>
## Specific Ideas

- "Deploy frequency should track runtime risk, not repository activity"
- "Defaults in deploy paths create silent misroutes — the most dangerous class of infra error"
- "A deploy that does not produce a healthy service is a failed deploy"
- "Most real outages are caught at health check, not during SSH"
- Include previous release SHA in deploy metadata for future rollback automation (release-governor territory)

</specifics>

<deferred>
## Deferred Ideas

- Staging vs production deploy targets (DEPLOY-04)
- Rollback workflow (DEPLOY-05)
- Required reviewers / wait timers on production Environment

</deferred>

---

*Phase: 11-deploy-automation*
*Context gathered: 2026-02-15*
