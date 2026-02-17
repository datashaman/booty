---
phase: 32-architect-foundation
verified: 2026-02-17
status: passed
---

# Phase 32 Verification

**Phase goal:** Architect config, triggering from Planner completion, input ingestion.

**Verification:** Codebase check against must_haves.

## must_haves

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Architect subscribes to Planner completion (never from GitHub labels) | ✓ | main.py _planner_worker_loop: Architect runs only after process_planner_job returns; no agent:architect label trigger |
| 2 | ArchitectConfig in .booty.yml: enabled, rewrite_ambiguous_steps, enforce_risk_rules | ✓ | architect/config.py ArchitectConfig; test_runner/config.py architect field |
| 3 | Architect receives plan, normalized_input, optional repo_context, optional issue_metadata | ✓ | architect/input.py ArchitectInput |
| 4 | Architect operates when repo_context is missing | ✓ | ArchitectInput.repo_context=None default; process_architect_input accepts None |
| 5 | Unknown keys in architect block fail Architect only | ✓ | get_architect_config raises ArchitectConfigError; BootyConfigV1 loads architect as raw dict |
| 6 | Planner cache hit skips Architect, enqueues Builder | ✓ | main.py: if result.cache_hit → should_enqueue_builder = True |
| 7 | Invalid architect config: post comment, apply label, block Builder | ✓ | ArchitectConfigError → post_architect_invalid_config_comment, add_architect_review_label |
| 8 | Architect enabled + approved enqueues Builder | ✓ | process_architect_input → approved → should_enqueue_builder |

## human_verification

None required.

## gaps

None.
