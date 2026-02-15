# Phase 9: Diff Limits + .booty.yml Schema v1 — Verification

**Phase:** 09-diff-limits-schema-v1
**Goal:** Enforce diff limits and validate extended .booty.yml schema.
**Verified:** 2026-02-15

---

## status: passed

---

## Must-Haves Verified

### 1. Verifier rejects PR exceeding max_files_changed or max_diff_loc (check failure)
**Status:** ✓

- `check_diff_limits()` in limits.py enforces both (lines 81-99)
- Runner calls check_diff_limits before clone for agent PRs; failures → edit_check_run(conclusion="failure")
- Verified in runner.py lines 89-103

### 2. Optional max_loc_per_file enforced for pathspec-matched safety-critical dirs
**Status:** ✓

- LimitsConfig.max_loc_per_file (default 250)
- Pathspec excludes tests/ by default (DEFAULT_MAX_LOC_PER_FILE_EXCLUDE = ["tests/**"])
- Per-file check in check_diff_limits uses pathspec.match_file for scope

### 3. .booty.yml with schema_version: 1 validated; unknown/malformed config fails check
**Status:** ✓

- BootyConfigV1 has model_config = ConfigDict(extra="forbid")
- load_booty_config_from_content and load_booty_config both dispatch by schema_version
- ValidationError caught in runner (early path and clone path)

### 4. Schema supports: test_command, setup_command?, timeout_seconds, max_retries, allowed_paths, forbidden_paths, allowed_commands, network_policy, labels
**Status:** ✓

- BootyConfigV1 in config.py lines 74-110: all fields present
- setup_command optional (str | None)
- network_policy: Literal["deny_all", "registry_only", "allow_list"] | None

### 5. Backward compat: repos without schema_version use v0 (existing BootyConfig)
**Status:** ✓

- _parse_booty_config: data.get("schema_version") == 1 → BootyConfigV1, else BootyConfig
- BootyConfig accepts extra keys (default Pydantic behavior)
- load_booty_config returns BootyConfig for v0/absent

---

## Score: 5/5 must-haves verified

---

## Human Verification Checklist

None required — automated checks sufficient.

---

## Gaps

None.
