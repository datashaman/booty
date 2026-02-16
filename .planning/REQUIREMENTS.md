# Requirements: Booty v1.6 Memory Agent

**Defined:** 2026-02-16
**Core Value:** A Builder agent that can take a GitHub issue and produce a working PR with tested code — the foundation everything else builds on.

## v1 Requirements

Requirements for milestone v1.6. Each maps to roadmap phases.

### Storage

- [ ] **MEM-01**: Memory persists records to append-only `memory.jsonl` in configured state dir
- [ ] **MEM-02**: Writes are atomic (append with fsync); reads tolerate partial last line
- [ ] **MEM-03**: Records use stable schema with common fields (id, type, timestamp, repo, sha, pr_number, source, severity, fingerprint, title, summary, paths, links, metadata)
- [ ] **MEM-04**: Retention keeps last 90 days by default (configurable); old records may be compacted
- [ ] **MEM-05**: Records survive restarts and are durable

### Ingestion

- [ ] **MEM-06**: Observability issue-from-Sentry → store `incident` record
- [ ] **MEM-07**: Governor HOLD decisions → store `governor_hold` record
- [ ] **MEM-08**: Governor deploy workflow failures → store `deploy_failure` record
- [ ] **MEM-09**: Security FAIL blocks → store `security_block` record
- [ ] **MEM-10**: Security ESCALATE (permission surface) → store `security_block` with reason
- [ ] **MEM-11**: Verifier FAIL (import/compile/test) → store `verifier_cluster` record
- [ ] **MEM-12**: Revert commits on main (detect via "Revert" or explicit input) → store `revert` record
- [ ] **MEM-13**: `memory.add_record(record)` API available for agents without direct adapter
- [ ] **MEM-14**: Dedup by (type, repo, sha, fingerprint, pr_number) within 24h window

### Lookup

- [ ] **MEM-15**: Lookup accepts candidate change (paths, repo, head sha) and returns matches from last 90 days
- [ ] **MEM-16**: Matches by path intersection OR fingerprint match to known failure classes
- [ ] **MEM-17**: Results sorted by severity desc, recency desc, path overlap count desc
- [ ] **MEM-18**: Matching is deterministic (no embeddings); fast (<1s for 10k records)

### Surfacing

- [ ] **MEM-19**: On Builder PR open/update: post or update ONE comment titled "Memory: related history" (marker `<!-- booty-memory -->`)
- [ ] **MEM-20**: PR comment includes up to 3 matches (type, date, summary, link); configurable max
- [ ] **MEM-21**: On Governor HOLD: include 1-2 memory links when hold reason matches prior incidents
- [ ] **MEM-22**: On Observability incident issue creation: append "Related history" section with up to 3 matches
- [ ] **MEM-23**: Memory is informational only; no outcomes blocked or altered

### Config

- [ ] **MEM-24**: Extend .booty.yml with optional `memory` block: enabled, retention_days, max_matches, comment_on_pr, comment_on_incident_issue
- [ ] **MEM-25**: Unknown keys in memory block fail for Memory only; do not break other agents
- [ ] **MEM-26**: Env overrides: MEMORY_ENABLED, MEMORY_RETENTION_DAYS, MEMORY_MAX_MATCHES

### CLI

- [ ] **MEM-27**: `booty memory status` — prints enabled, record count, retention
- [ ] **MEM-28**: `booty memory query --pr <n>` or `--sha <sha>` — prints matches; supports `--json`

## Future Requirements

Deferred to later milestones.

| ID | Requirement | Deferred because |
|----|-------------|------------------|
| — | Embeddings / vector DB / semantic search | Explicitly out of scope for v1 |
| — | Auto-remediation, blocking, policy changes | Memory is informational only |

## Out of Scope

| Feature | Reason |
|---------|--------|
| Embeddings / vector DB / search platform | Spec: deterministic lookup in v1; no ML |
| Fine-tuning / ML scoring | Spec: no ML |
| Automatic blocking, throttling, policy changes | Spec: Memory does not alter outcomes |
| PR creation, deploy actions from Memory | Spec: informational only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MEM-01 | 22 | Complete |
| MEM-02 | 22 | Complete |
| MEM-03 | 22 | Complete |
| MEM-04 | 22 | Complete |
| MEM-05 | 22 | Complete |
| MEM-06 | 23 | Pending |
| MEM-07 | 23 | Pending |
| MEM-08 | 23 | Pending |
| MEM-09 | 23 | Pending |
| MEM-10 | 23 | Pending |
| MEM-11 | 23 | Pending |
| MEM-12 | 23 | Pending |
| MEM-13 | 22 | Complete |
| MEM-14 | 22 | Complete |
| MEM-15 | 24 | Pending |
| MEM-16 | 24 | Pending |
| MEM-17 | 24 | Pending |
| MEM-18 | 24 | Pending |
| MEM-19 | 25 | Pending |
| MEM-20 | 25 | Pending |
| MEM-21 | 25 | Pending |
| MEM-22 | 25 | Pending |
| MEM-23 | 25 | Pending |
| MEM-24 | 22 | Complete |
| MEM-25 | 22 | Complete |
| MEM-26 | 22 | Complete |
| MEM-27 | 26 | Pending |
| MEM-28 | 26 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-16*
*Last updated: 2026-02-16 after roadmap creation*
