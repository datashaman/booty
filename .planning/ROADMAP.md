# Roadmap: Booty

## Milestones

- ✅ **v1.8 Architect Agent** — Phases 32–36 (shipped 2026-02-17) — [Full details](milestones/v1.8-ROADMAP.md)
- ✅ **v1.7 Planner Agent** — Phases 27–31 (shipped 2026-02-16) — [Full details](milestones/v1.7-ROADMAP.md)
- ✅ **v1.6 Memory Agent** — Phases 22–26 (shipped 2026-02-16) — [Full details](milestones/v1.6-ROADMAP.md)
- ✅ **v1.5 Security Agent** — Phases 18–21 (shipped 2026-02-16) — [Full details](milestones/v1.5-ROADMAP.md)
- v1.0–v1.4 — Archived in `.planning/milestones/`

## Next Milestone

**v1.9 Reviewer Agent** — Phases 37–41 — [Full details](milestones/v1.9-ROADMAP.md)

| # | Phase | Goal | Requirements | Status |
|---|-------|------|---------------|--------|
| 37 | Skeleton + Check Plumbing | Module, config, check run, comment upsert | REV-04, REV-10, REV-12, REV-13 | ✓ |
| 38 | Agent PR Detection + Event Wiring | Webhook, dedup, agent filter | REV-01, REV-02, REV-03, REV-05 | ✓ |
| 39 | Review Engine | LLM prompt, rubric, block_on mapping | REV-06, REV-07, REV-08, REV-11 | ✓ |
| 40 | Promotion Gating | Builder requires reviewer success | REV-14 | ✓ |
| 41 | Fail-Open + Metrics | Failure handling, metrics, docs | REV-09, REV-15 | ✓ |

---
*Last updated: 2026-02-17 — Phase 41 complete; v1.9 milestone complete*
