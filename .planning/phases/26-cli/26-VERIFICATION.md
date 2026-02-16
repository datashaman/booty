---
phase: 26-cli
goal: "CLI — booty memory status, query (MEM-27, MEM-28)"
verified: 2026-02-16
---

status: passed

## Must-Haves Verified

| ID | Requirement | Status |
|----|-------------|--------|
| MEM-27 | booty memory status prints enabled, record count, retention_days | ✓ |
| MEM-28 | booty memory query --pr \<n\> prints matches; supports --json | ✓ |
| MEM-28 | booty memory query --sha \<sha\> prints matches; supports --json | ✓ |
| - | Memory disabled shows 'Memory disabled' and exits 0 | ✓ |
| - | GITHUB_TOKEN required for query; clear error when missing | ✓ |

## Artifacts Checked

- `src/booty/cli.py` — `memory_status`, `memory_query` implemented
- `tests/test_memory_cli.py` — 11 unit tests passing

## Verification Method

- Manual: `booty memory status` (disabled), `booty memory status --workspace /tmp/booty-26-test` (enabled)
- pytest tests/test_memory_cli.py: 11 passed
