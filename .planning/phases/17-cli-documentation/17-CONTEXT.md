# Phase 17: CLI & Documentation - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

booty governor CLI (status, simulate, trigger) and docs/release-governor.md. status exists from Phase 14; this phase adds simulate and trigger, and creates operator/dev documentation. No new Governor capabilities — only CLI surface and docs.

</domain>

<decisions>
## Implementation Decisions

### simulate output
- **Format:** Same style as status — key/value lines (e.g. `decision: HOLD`, `risk_class: HIGH`, `reason: high_risk_no_approval`)
- **Paths:** Optional via `--verbose` or `--show-paths` — include paths that drove risk when flag present
- **GitHub requirement:** Fail with clear instructions when GITHUB_TOKEN missing: "GITHUB_TOKEN required for simulate; set it to fetch diff"
- **Content:** Show context (production_sha, first deploy, degraded, approval status) plus unblock hint when HOLD

### trigger when blocked
- **Exit:** Exit 1; print decision + reason + unblock hint; do not create status/issue from CLI
- **Unblock hint:** Bullet list of options — each approval method with exact action (e.g. "Add label release:approved" or "Set GOV_APPROVE=1")
- **Force/override:** No — trigger always respects approval; no `--force` flag
- **Success output:** Verbose — run URL + SHA + timestamp

### CLI style
- **SHA argument:** Both `--sha` and positional; positional as shorthand (e.g. `booty governor simulate abc123`)
- **Machine-readable:** Add `--json` to simulate, trigger, and status
- **Consistency:** Match verifier/check-test style — similar option names, key=value output where applicable
- **Repo context:** cwd by default (read .booty.yml, infer repo from git remote); optional `--repo` to override

### release-governor docs
- **Audience:** Both operators (run deploy, use CLI) and devs (configure .booty.yml)
- **Style:** Quick reference plus setup/troubleshooting
- **Sections:** Intro/overview, execution flow (when Governor runs), dedicated CLI reference, config, approval mechanism, troubleshooting, manual test steps
- **Examples:** Inline in each section; no separate examples section

### Claude's Discretion
- Exact `--verbose` vs `--show-paths` flag name for simulate
- JSON output field structure
- Repo inference from git remote when not explicit
- Exact unblock hint phrasing per approval mode

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 17-cli-documentation*
*Context gathered: 2026-02-16*
