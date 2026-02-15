# Feature Research: Verifier Agent

**Domain:** PR verification, CI gating, error-rate control
**Researched:** 2026-02-15
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Run tests in clean env | Verifier must not inherit Builder's workspace state | LOW | Reuse `prepare_workspace` pattern — clone PR branch, run `execute_tests` |
| Block PR if red | Core value: gate merge on verification | MEDIUM | Checks API `conclusion: failure` + promotion control |
| Enforce diff limits | Blast-radius control (user-specified) | MEDIUM | max_files_changed, max_diff_loc, max_loc_per_file (optional per-path) |
| Validate .booty.yml | Deterministic execution; fail fast if config invalid | LOW | Extend existing BootyConfig; schema_version: 1 |
| Detect hallucinated imports / compile failures | LLMs invent imports; must catch before test run | MEDIUM | AST parse changed files, validate imports exist; run setup/test with early failure capture |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Universal visibility, selective authority | Every PR gets Verifier comment; only agent PRs get merge gate | LOW | Builds trust; humans see Verifier output without being blocked |
| Required check `booty/verifier` | Branch protection can require it; hard merge gate | LOW | GitHub UI shows required checks clearly |
| .booty.yml schema v1 | Repo-level config: allowed_paths, network_policy, etc. | MEDIUM | Enables sandboxing, deterministic execution |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Rely on CI only | "CI already runs tests" | CI reports; Verifier decides. Separation of concerns. | Verifier runs own tests; can optionally aggregate CI results later |
| Block all PRs equally | Simplicity | User specified: enforce only for agent PRs | Use `agent:builder` label or bot author check |
| Dynamic .booty.yml from PR | Flexibility | Non-deterministic; security risk | Config from base branch only |

## Feature Dependencies

```
GitHub App auth
    └──requires──> Checks API (create_check_run)
                        └──enables──> Required status check, merge gate

pull_request webhook
    └──requires──> Webhook handler for pull_request (opened, synchronize)
    └──provides──> PR context (head_sha, repo, labels, author)

.booty.yml schema v1
    └──requires──> Extend BootyConfig (allowed_paths, forbidden_paths, etc.)
    └──enables──> Diff limits, network policy, deterministic execution

Clean env test run
    └──requires──> Clone PR branch (fresh)
    └──reuses──> execute_tests() from test_runner
```

## MVP Definition (v1.2)

### Launch With

- [ ] GitHub App auth path for Verifier (checks:write)
- [ ] pull_request webhook handler (opened, synchronize)
- [ ] Create check run `booty/verifier` (queued → in_progress → completed)
- [ ] Run tests in clean env (clone PR head, execute_tests)
- [ ] Block PR if tests fail (conclusion: failure)
- [ ] Enforce gates only for agent PRs (label or author check)
- [ ] .booty.yml validation (schema_version: 1)
- [ ] Diff limits: max_files_changed, max_diff_loc
- [ ] Detect compile/import failures (AST + early subprocess failure)

### Add After Validation

- [ ] max_loc_per_file for safety-critical dirs (pathspec-scoped)
- [ ] network_policy, allowed_commands in .booty.yml
- [ ] Optional: aggregate CI check results (defer)

### Future Consideration

- [ ] Integration tests generation (Builder) — deferred
- [ ] Multi-repo Verifier (single App, multiple installations)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Checks API + block if red | HIGH | MEDIUM (App auth) | P1 |
| Clean env test run | HIGH | LOW (reuse) | P1 |
| .booty.yml validation | HIGH | LOW | P1 |
| Diff limits (files, LOC) | HIGH | MEDIUM | P1 |
| Import/compile detection | HIGH | MEDIUM | P1 |
| Selective enforcement | HIGH | LOW | P1 |
| max_loc_per_file per-path | MEDIUM | MEDIUM | P2 |

## Sources

- User requirements (booty/verifier, selective authority, .booty.yml schema)
- PROJECT.md validated requirements
- Existing test_runner, webhooks architecture

---
*Feature research for: Verifier agent (Booty v1.2)*
*Researched: 2026-02-15*
