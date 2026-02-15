# Pitfalls Research: Verifier Agent

**Domain:** Adding Verifier to Booty
**Researched:** 2026-02-15
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: PAT for Checks API

**What goes wrong:**
Verifier tries to create check runs with `GITHUB_TOKEN` (PAT). GitHub returns 403 Forbidden. Checks API refuses PAT authentication.

**Why it happens:**
GitHub docs: "OAuth apps and authenticated users cannot create check runs." Only GitHub Apps can. Booty currently uses PAT everywhere.

**How to avoid:**
- Add GitHub App authentication path before any Checks API work
- Use `Auth.AppAuth(app_id, private_key)` and `GithubIntegration.get_github_for_installation()`
- Verifier module must use App token exclusively for `create_check_run` / `edit`

**Warning signs:**
- Tests or manual runs fail with 403 on POST to `/repos/.../check-runs`
- Assumption "we already have a token" without checking Checks API requirements

**Phase to address:**
Phase 1 (GitHub App + Checks integration)

---

### Pitfall 2: Verifier Runs on Wrong Branch

**What goes wrong:**
Verifier clones `main` or base branch instead of PR head. Tests run against wrong code. Check passes/fails incorrectly.

**Why it happens:**
Builder uses `prepare_workspace` which clones base and creates new branch. Verifier needs to verify PR head specifically.

**How to avoid:**
- Verifier must clone/fetch PR head ref (`refs/pull/{id}/head` or branch name)
- Use `head_sha` from webhook payload — that's the commit to verify
- Document: "Verifier always runs against head_sha"

**Warning signs:**
- Check passes but merged code fails
- Tests pass locally (on head) but Verifier shows fail (if it ran on base)

**Phase to address:**
Phase 2 (Verifier runner — clone at head)

---

### Pitfall 3: Blocking Human PRs

**What goes wrong:**
Verifier sets `conclusion: failure` for all failing PRs. Human developers get merge blocked by Booty's check. User wanted "selective authority."

**Why it happens:**
Implementation defaults to "all PRs" unless explicitly checking agent PR criteria.

**How to avoid:**
- Always run Verifier for every PR (universal visibility); always post check with real conclusion (success/failure)
- Builder promotion: only skip when Verifier fails and it's an agent PR
- Merge gate: GitHub branch protection is repo-level. User adds booty/verifier to required checks if desired. Document: for mixed repos, add only to agent branches or accept all PRs must pass

**Warning signs:**
- Human developers complain Verifier blocks their PRs
- Need to document when to add booty/verifier to branch protection

**Phase to address:**
Phase 1 (clarify in requirements); Phase 2 (implementation)

---

### Pitfall 4: .booty.yml Schema Breaking Change

**What goes wrong:**
New schema (allowed_paths, forbidden_paths, etc.) breaks existing repos with old .booty.yml. Builder and Verifier both fail.

**Why it happens:**
Adding required fields or renaming without backward compatibility.

**How to avoid:**
- Use `schema_version: 1`; old configs without it use v0 (current BootyConfig)
- New fields optional with sensible defaults
- Validator: if schema_version >= 1, apply stricter validation

**Warning signs:**
- Existing Booty repos start failing after Verifier deploy
- `load_booty_config` raises ValidationError for previously-valid configs

**Phase to address:**
Phase 3 (.booty.yml schema extension)

---

### Pitfall 5: Race Between Builder and Verifier

**What goes wrong:**
Builder opens PR. Verifier webhook fires. Verifier starts cloning. Builder's push just landed; Verifier gets partial/wrong state. Or: Verifier runs before Builder finishes pushing.

**Why it happens:**
Webhook delivery is async; clone happens seconds after push. Usually fine. Edge case: very fast Builder, slow Verifier.

**How to avoid:**
- Verifier uses `head_sha` from webhook — that's the exact commit. Clone that ref.
- GitHub ensures `head_sha` is the PR head at webhook delivery time. No race for same PR event.
- Multiple pushes: each triggers `synchronize`; each has new `head_sha`. Verifier runs for each. Last run wins. Acceptable.

**Warning signs:**
- Flaky "check ran on wrong commit" reports
- Use `head_sha` consistently; log it in check output

**Phase to address:**
Phase 2 (Verifier runner)

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Checks API | Using PAT | GitHub App with `checks:write` |
| Clone PR head | Cloning default branch | `git fetch origin pull/ID/head:pr-BRANCH` or checkout `refs/pull/ID/head` |
| Webhook | Ignoring `synchronize` | Handle both `opened` and `synchronize` — PRs get multiple commits |

## "Looks Done But Isn't" Checklist

- [ ] **Checks API:** Verify 403 is gone — use App token, not PAT
- [ ] **Clone:** Verify `head_sha` matches PR head in GitHub UI
- [ ] **Selective enforcement:** Document branch protection setup for mixed repos
- [ ] **.booty.yml:** Test with old format (no schema_version) still works

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| PAT for Checks | Phase 1 | Manual: create check run with App; confirm 201 |
| Wrong branch | Phase 2 | E2E: PR with known fail; check fails |
| Blocking humans | Phase 1/2 | Document; test with human-authored PR |
| Schema break | Phase 3 | Run against repo with old .booty.yml |
| Race | Phase 2 | Use head_sha; log in check output |

---
*Pitfalls research for: Verifier agent (Booty v1.2)*
*Researched: 2026-02-15*
