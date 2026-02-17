# Builder–Planner Integration Audit

**Date:** 2026-02-17  
**Scope:** Verify Builder–Planner integration implemented in v1.7+ works end-to-end

---

## Executive Summary

**The Builder–Planner integration is implemented and works.** It was completed as part of v1.7 (and subsequent refinements). The system uses a unified `agent` label for both Planner and Builder; Planner runs first when that label is applied; when a plan exists, Builder executes it. No additional milestone work is needed for basic integration.

---

## What Was Implemented

### 1. Trigger and Flow

| Component | Behavior |
|-----------|----------|
| **TRIGGER_LABEL** | Default `"agent"` (config.py L17). One label for Planner + Builder. |
| **Webhook branch order** | Planner branch runs first; if `agent` label + planner enabled → enqueue Planner, return 202. |
| **Builder branch** | Only reached when plan trigger doesn't match. If no plan and planner enabled → safety net: enqueue Planner instead; Planner worker will enqueue Builder when done. |
| **Planner worker** | After `process_planner_job` completes, autonomously enqueues Builder (main.py L308–331). Skips if Builder already queued for same issue (race avoidance). |

### 2. Plan Resolution

| Step | Location | Behavior |
|------|----------|----------|
| **get_plan_for_issue** | planner/store.py | 1) Try local file `plans/<owner>/<repo>/<issue>.json` 2) Fall back to GitHub issue comments (marker `<!-- booty-plan -->`) |
| **Builder process_job** | main.py L147 | Calls `get_plan_for_issue`; if `None` → `post_builder_blocked_comment`, return early. |
| **Webhook** | webhooks.py L716 | Same check before enqueueing Builder; if no plan → enqueue Planner (safety net) or block. |

### 3. Builder Consumption of Plan

| Consumer | Location | What it uses |
|----------|----------|--------------|
| **_analysis_from_plan** | code_gen/generator.py L38–56 | `plan.goal`, `plan.steps` (edit/add paths, acceptance), `handoff_to_builder.commit_message_hint`, `handoff_to_builder.pr_title` |
| **IssueAnalysis** | generator L152–159 | When `planner_plan` is not None: derives analysis from plan; **no LLM issue interpretation** |
| **Commit message** | generator L426–429 | Uses `planner_plan.handoff_to_builder.commit_message_hint` |
| **PR title** | generator L466–467 | Uses `planner_plan.handoff_to_builder.pr_title` |
| **process_issue_to_pr** | main.py L162 | Passes `planner_plan=plan` from process_job |

### 4. Blocked-Without-Plan UX

When Builder would run but no plan exists (e.g. Planner disabled):

- `post_builder_blocked_comment` (github/comments.py L268)
- Tells user: "Add `agent` to generate a plan first, or ensure a plan exists for this issue."

### 5. Observability → Planner → Builder

Observability creates issues with `settings.TRIGGER_LABEL` (webhooks.py L913 → "agent"). When that label is applied:

1. Webhook receives `issues.labeled` or `issues.opened` with `agent`
2. Planner branch runs (is_plan_trigger)
3. Planner enqueued → generates plan → stores + posts comment
4. Planner worker enqueues Builder for same issue
5. Builder runs with plan from local file or GitHub comment

---

## Test Coverage

| Area | Tests | Result |
|------|-------|--------|
| get_plan_for_issue | test_get_plan_for_issue_prefers_local_file, test_get_plan_for_issue_fallback_to_github_when_no_local | ✓ Pass |
| Plan schema, storage, cache | test_planner_*, test_planner_schema | ✓ 80 selected, all pass |
| process_job with plan | test_sentry_integration (mocks get_plan_for_issue, process_issue_to_pr) | ✓ Pass |
| Full suite | 247 tests | ✓ All pass |

---

## Gaps / Edge Cases

1. **No end-to-end integration test** that runs real Planner → Builder without mocks. Manual verification would require a live GitHub repo and webhook.
2. **PLAN-22 remains deferred** in requirements: "Builder can execute the plan without needing clarifications" — intended as verification when Builder integrates. Integration exists; "without clarifications" is qualitative and not formally verified.
3. **agent:builder vs agent** — Legacy docs mention `agent:builder`; config default is `agent`. Verifier and PR labels use `settings.TRIGGER_LABEL`, so behavior is consistent. `.env.example` documents `TRIGGER_LABEL=agent`.

---

## Conclusion

Builder–Planner integration is implemented and functioning:

- Planner runs on `agent` label
- Builder requires a plan; blocks or triggers Planner if missing
- Planner worker autonomously enqueues Builder when plan is ready
- Builder consumes plan (goal, steps, handoff_to_builder) for analysis, commit, PR title
- Observability creates issues with same label → full loop works

**Recommendation:** Do not scope a new milestone for "Builder integration consuming Planner output" — it is done. Consider instead:

- **E2E test** (optional): Add a test that runs Planner job → Builder job in-process with mocked GitHub/Sentry.
- **PLAN-22 closeout**: Update v1.7 requirements to mark PLAN-22 satisfied if you're satisfied with current behavior.
- **Next milestone focus**: Other improvements (e.g. plan quality, step fidelity, Observability incident→Plan flow refinements).
