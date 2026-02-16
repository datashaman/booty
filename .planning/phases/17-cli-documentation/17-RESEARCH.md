# Phase 17: CLI & Documentation — Research

## RESEARCH COMPLETE

**Phase:** 17
**Gathered:** 2026-02-16

---

## What You Need to Know to Plan This Phase

### 1. Existing Assets (Phase 14–16)

**CLI status already exists** (`src/booty/cli.py`):
- `booty governor status` — shows release state (production_sha_current, last_deploy_*, etc.)
- Loads config via `load_booty_config(Path.cwd())`, `is_governor_enabled(config)`
- Uses `get_state_dir()`, `load_release_state(state_dir)` from store

**Governor core**:
- `handler.py`: `handle_workflow_run(payload, config)` → Decision; needs payload (repo, head_sha), config
- `handler` uses PyGithub `repo.compare(production_sha, head_sha)` for diff; calls `compute_risk_class`, `compute_decision`
- `decision.py`: `compute_decision(head_sha, risk_class, config, state, state_dir, degraded, approval_context, is_first_deploy)` → Decision
- `risk.py`: `compute_risk_class(comparison, config)` → "LOW"|"MEDIUM"|"HIGH"; does NOT return matching paths
- `deploy.py`: `dispatch_deploy(gh_repo, config, head_sha)` — workflow_dispatch with sha input

** approval_context** in handler: `env_approved`, `label_approved`, `comment_approved`. For CLI: only `env_approved` matters (from `RELEASE_GOVERNOR_APPROVED`). Label/comment require PR/event context; CLI runs in local env.

### 2. simulate — Implementation Path

**Goal:** Dry-run decision for a given SHA; no deploy.

**Required:**
1. Load config: `load_booty_config(Path.cwd())` (or --workspace)
2. Resolve repo: cwd → `git remote get-url origin` (fallback) or explicit `--repo owner/repo`
3. Load state: `load_release_state(get_state_dir())`
4. Get comparison: `gh_repo.compare(production_sha, head_sha)` — **requires GITHUB_TOKEN**
5. Compute: `compute_risk_class(comparison, config)`, `compute_decision(...)` with `approval_context={"env_approved": bool from env, "label_approved": False, "comment_approved": False}`
6. Output: key/value lines; on HOLD include unblock hint per approval mode

**Paths for risk:** `risk.compute_risk_class` only returns risk class. To show paths: extend `compute_risk_class` with optional return of matching paths, or add `get_risk_paths(comparison, config)` that returns `(risk_class, list[str])`. Simpler: add `get_risk_paths` or extend with `return_paths: bool` in a new helper to avoid changing existing callers.

**Unblock hints** (from webhooks.py / ux.py):
- mode=label: "Add label {approval_label}"
- mode=comment: "Comment {approval_command}"
- mode=environment: "Set RELEASE_GOVERNOR_APPROVED=true"

### 3. trigger — Implementation Path

**Goal:** Manual deploy trigger; respects approval (no --force).

**Flow:**
1. Reuse simulate logic to compute decision
2. If HOLD: exit 1; print decision, reason, unblock hint; no status/issue
3. If ALLOW: `dispatch_deploy(gh_repo, config, head_sha)`; update release state (last_deploy_attempt_sha, last_deploy_time, pending); output run URL if obtainable (workflow_dispatch returns 204, no run URL — can only provide generic Actions URL)
4. Success output: SHA, timestamp, link to Actions runs

**GITHUB_TOKEN:** Required for both simulate and trigger (API calls).

### 4. Repo Inference

- `git remote get-url origin` → parse to owner/repo (e.g. `git@github.com:owner/repo.git` → `owner/repo`)
- Use `giturlparse` if already in project; else simple regex/split
- Fallback: require `--repo` if cannot infer

### 5. JSON Output

- `--json` on status, simulate, trigger
- Structure: `{"decision":"HOLD","reason":"high_risk_no_approval","risk_class":"HIGH",...}` for simulate; similar for status (state dict); trigger success: `{"outcome":"ALLOW","sha":"...","triggered_at":"..."}`

### 6. docs/release-governor.md

**Audience:** Operators (run deploy, use CLI) and devs (configure .booty.yml).

**Sections (from 17-CONTEXT):**
- Intro/overview
- Execution flow (when Governor runs — verification workflow completes on main)
- CLI reference (status, simulate, trigger)
- Config (ReleaseGovernorConfig fields, env overrides)
- Approval mechanism (env, label, comment)
- Troubleshooting (common holds, how to unblock)
- Manual test steps (simulate various SHAs, trigger when ALLOW)

**Style:** Quick reference; inline examples; no separate examples section. Match deploy-setup.md tone.

### 7. Testing

- Unit tests: mock PyGithub Compare, test simulate/trigger output
- Integration: `booty governor simulate <sha>` with real token in CI (optional)
- Docs: manual steps for operator

---

## Blockers / Open Questions

None. All dependencies (handler, decision, risk, deploy, store) exist. Phase 17 is additive.

---

*Research complete.*
