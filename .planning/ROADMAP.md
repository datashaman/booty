# Roadmap: Booty

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-02-14)
- ✅ **v1.1 Test Generation & PR Promotion** — Phases 5-6 (shipped 2026-02-15)
- ✅ **v1.2 Verifier Agent** — Phases 7-10 (shipped 2026-02-15)
- ✅ **v1.3 Observability** — Phases 11-13 (shipped 2026-02-15)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-02-14</summary>

Delivered a Builder agent that picks up GitHub issues, writes code via LLM, runs tests with iterative refinement, and opens PRs — including against its own repository.

**Stats:** 77 files, 3,012 LOC Python, 4 phases, 13 plans, 1 day execution

See [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) and [MILESTONES.md](MILESTONES.md) for details.

</details>

<details>
<summary>✅ v1.1 Test Generation & PR Promotion (Phases 5-6) — SHIPPED 2026-02-15</summary>

Builder generates unit tests for all changed files and promotes draft PRs to ready-for-review when tests and linting pass.

**Stats:** 4 plans, 2 phases, 41 files modified (v1.0..v1.1)

See [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md) and [MILESTONES.md](MILESTONES.md) for details.

</details>

<details>
<summary>✅ v1.2 Verifier Agent (Phases 7-10) — SHIPPED 2026-02-15</summary>

Verifier agent runs on every PR, runs tests in clean env, enforces diff limits, validates .booty.yml, detects import/compile failures, posts check run `booty/verifier`.

**Stats:** 68 files modified (v1.1..v1.2), 4 phases, 12 plans

See [milestones/v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md) and [MILESTONES.md](MILESTONES.md) for details.

</details>

<details>
<summary>✅ v1.3 Observability (Phases 11-13) — SHIPPED 2026-02-15</summary>

Automated deployment via GitHub Actions; Sentry APM; observability agent (Sentry webhook → filtered → GitHub issues with agent:builder label).

**Stats:** 58 files modified (v1.2..v1.3), 3 phases, 5 plans, 6,805 LOC Python

See [milestones/v1.3-ROADMAP.md](milestones/v1.3-ROADMAP.md) and [MILESTONES.md](MILESTONES.md) for details.

</details>

---

## Progress

| Phase | Milestone | Goal | Status |
|-------|-----------|------|--------|
| 1. Foundation | v1.0 | Webhook, clone, job queue | Complete |
| 2. GitHub Integration | v1.0 | LLM, PR creation | Complete |
| 3. Test-Driven Refinement | v1.0 | Tests, refinement loop | Complete |
| 4. Self-Modification Safety | v1.0 | Protected paths, draft PR | Complete |
| 5. Test Generation | v1.1 | Unit tests for changed files | Complete |
| 6. PR Promotion | v1.1 | Draft → ready when green | Complete |
| 7. GitHub App + Checks | v1.2 | Checks API integration | Complete |
| 8. Verifier Runner | v1.2 | PR webhook, clone, test, check | Complete |
| 9. Diff Limits + Schema | v1.2 | Limits, .booty.yml v1 | Complete |
| 10. Import/Compile Detection | v1.2 | Hallucination detection | Complete |
| 11. Deploy Automation | v1.3 | GitHub Actions → SSH → DO, deploy.sh | Complete |
| 12. Sentry APM | v1.3 | Error tracking, release/SHA correlation | Complete |
| 13. Observability Agent | v1.3 | Sentry webhook → filter → GitHub issues | Complete |

---
*Last updated: 2026-02-15 — v1.3 milestone complete*
