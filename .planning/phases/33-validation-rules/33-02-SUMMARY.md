---
phase: 33-validation-rules
plan: 02
subsystem: architect
tags: rewrite, ambiguity, overreach

requires:
  - phase: 33-01
    provides: validation, derive_touch_paths
provides:
  - check_ambiguity, check_overreach, rewrite_ambiguous_steps, try_rewrite_overreach
affects: 33-03

key-files:
  created: src/booty/architect/rewrite.py, tests/test_architect_rewrite.py
  modified: src/booty/architect/__init__.py

duration: ~10min
completed: 2026-02-17
---

# Phase 33-02: Ambiguity & Overreach Summary

**rewrite.py with check_ambiguity, check_overreach, rewrite_ambiguous_steps, try_rewrite_overreach; 11 unit tests**

## Accomplishments
- Ambiguity detection: short acceptance (<15 chars), vague patterns (fix, improve, as needed, etc.)
- rewrite_ambiguous_steps: flags when disabled; tightens when config.rewrite_ambiguous_steps enabled
- Overreach: repo-wide (≥8 paths, 3+ domains), multi-domain (2+ of src/tests/docs/infra/.github), speculative keywords
- try_rewrite_overreach: merge related steps when possible; returns (None, reasons) when block needed

## Task Commits
1. **Tasks 1-2** - feat(33-02): ambiguity and overreach detection and rewrite

---
*Phase: 33-validation-rules*
*Completed: 2026-02-17*
