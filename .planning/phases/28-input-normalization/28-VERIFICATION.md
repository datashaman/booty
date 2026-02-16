---
phase: 28-input-normalization
status: passed
verified: 2026-02-16
---

# Phase 28: Input Normalization — Verification

**Status:** passed ✓

## Must-Haves Checked Against Codebase

### 28-01: PlannerInput model and normalizers

| Must-Have | Verified | Evidence |
|-----------|----------|----------|
| Planner accepts full GitHub Issue (title, body, labels) | ✓ | input.py normalize_github_issue |
| Planner accepts CLI text via goal + body split | ✓ | input.py normalize_cli_text |
| Planner detects Observability incident (agent:incident or **Severity:**+**Sentry:**) | ✓ | derive_source_type, _looks_like_sentry_body |
| source_type: incident, feature_request, bug, unknown | ✓ | derive_source_type, LABEL_TO_SOURCE |
| Single PlannerInput (goal, body, labels, source_type, metadata) | ✓ | PlannerInput model |
| input.py provides PlannerInput, normalizers | ✓ | PlannerInput, normalize_github_issue, normalize_cli_text, normalize_from_job |
| Detection heuristics reference Sentry format | ✓ | **Severity:**, **Sentry:**, **Location:** in input.py |

### 28-02: get_repo_context

| Must-Have | Verified | Evidence |
|-----------|----------|----------|
| Optional repo context (default branch, tree 2-3 levels) | ✓ | get_repo_context max_depth=2 |
| get_repo_context returns {default_branch, tree} | ✓ | input.py get_repo_context |
| CLI plan --text infers repo from cwd when in git repo | ✓ | cli.py plan_text _infer_repo_from_git |
| input.py contains get_repo_context | ✓ | input.py:65 |
| get_repo_context uses get_contents, default_branch | ✓ | gh_repo.get_contents, default_branch |

### 28-03: Wire worker and CLI

| Must-Have | Verified | Evidence |
|-----------|----------|----------|
| Webhook planner worker uses normalize_from_job | ✓ | worker.py process_planner_job |
| Plan built from PlannerInput.goal | ✓ | goal = inp.goal in worker, plan_issue, plan_text |
| booty plan --issue uses normalize_github_issue | ✓ | cli.py plan_issue |
| booty plan --text uses normalize_cli_text | ✓ | cli.py plan_text |
| plan_text infers repo from cwd when in git repo | ✓ | _infer_repo_from_git(ws) in plan_text |
| Optional repo context fetched when repo + token | ✓ | get_repo_context in worker, plan_issue, plan_text |
| worker provides process_planner_job consuming PlannerInput | ✓ | worker.py |
| cli provides plan_issue, plan_text consuming normalizers | ✓ | cli.py |

## Phase Goal

**Goal:** Normalize GitHub issue, Observability incident, and CLI text into Planner input context.

**Achieved:** ✓
- Full GitHub Issue → PlannerInput via normalize_github_issue
- Observability incident detected via label or body heuristics
- CLI text → PlannerInput via normalize_cli_text (goal/body split)
- Optional repo context (default branch, tree) when repo + token available
- Single PlannerInput flows through worker and CLI
