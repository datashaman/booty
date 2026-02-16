# Phase 17: CLI & Documentation — Verification

**Status:** passed
**Verified:** 2026-02-16

## Must-haves checked against codebase

### Phase goal success criteria

| Criterion | Verified |
|-----------|----------|
| booty governor status — show release state | ✓ cli.py governor_status |
| booty governor simulate --sha <sha> — dry-run decision (no deploy) | ✓ governor_simulate |
| booty governor trigger --sha <sha> — manual trigger (respects approval) | ✓ governor_trigger |
| docs/release-governor.md: config, approval, troubleshooting, manual test steps | ✓ 7 sections |

### Plan 17-01 must_haves

| Truth | Verified |
|-------|----------|
| simulate runs decision dry-run (no deploy) | ✓ Calls simulate_decision_for_cli |
| trigger dispatches on ALLOW; exit 1 on HOLD | ✓ dispatch_deploy on ALLOW; raise SystemExit(1) on HOLD |
| On HOLD: CLI prints decision, reason, unblock hint | ✓ _unblock_hints |
| GITHUB_TOKEN required; fail with clear message | ✓ ValueError "GITHUB_TOKEN required for simulate" |
| status, simulate, trigger support --json | ✓ as_json option on all three |

### Plan 17-02 must_haves

| Truth | Verified |
|-------|----------|
| docs/release-governor.md exists with config, approval, troubleshooting | ✓ |
| Manual test steps for simulate and trigger | ✓ Manual test steps section |
| CLI reference for status, simulate, trigger | ✓ CLI reference section |

## Score

7/7 phase criteria verified
All plan must_haves satisfied
