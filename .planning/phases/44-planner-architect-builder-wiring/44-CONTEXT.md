# Phase 44: Planner→Architect→Builder Wiring - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

For issue events with the trigger label: route to Planner, Architect, or Builder based on plan existence and Architect approval status. Builder consumes Architect artifact first; Planner fallback is configurable via compat flag. Add Architect as a standalone enqueue path from webhook when plan exists but unreviewed. Routing and config behavior must be auditable and documented.

</domain>

<decisions>
## Implementation Decisions

### Compat flag policy
- **Default:** Compat on — safe migration; Builder can use Planner plan when no Architect artifact
- **Intent:** Temporary migration aid — repos expected to eventually use Architect; compat off enforces Architect-only
- **Config:** Both env and file; env overrides file (same precedence as other Booty config)
- **Compat off + Planner plan only:** Route to Architect (enqueue Architect to produce artifact); do NOT block Builder with comment — Architect will approve, then Builder runs

### Architect trigger from webhook
- **When:** Any trigger event (label added, issue opened) with existing unreviewed plan → enqueue Architect
- **Dedupe:** Yes — do not re-run Architect on same issue+plan; dedupe so repeated label toggles don't spam Architect
- **Implementation:** Architect as its own enqueue path — ArchitectJob (or equivalent); separate job type/queue
- **Architect disabled + plan exists:** Builder uses Planner plan directly (Architect skipped)

### Disabled-agent behavior
- **Architect disabled + plan exists:** Builder uses Planner plan directly
- **Planner disabled + no plan:** Post builder_blocked, don't enqueue anyone
- **Planner disabled + Architect-approved plan exists:** Enqueue Builder only
- **Architect disabled + unreviewed plan:** Builder uses Planner plan (Architect skipped; compat allows fallback)

### Documentation expectations
- **Placement:** Both — separate doc (e.g. docs/routing.md) plus inline comments in router
- **Format:** Decision table — event + plan state → action
- **Config precedence:** Full documentation — env vs file vs default for each relevant flag
- **Disabled-agent behavior:** Enumerate every combination explicitly in docs

</decisions>

<specifics>
## Specific Ideas

- Compat is a migration lever, not a permanent opt-out
- Architect gets its own job type so webhook can enqueue it when plan exists unreviewed
- Dedupe prevents Architect re-runs on label toggling for same issue/plan
- Operator docs should be complete enough to debug routing without reading code

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 44-planner-architect-builder-wiring*
*Context gathered: 2026-02-17*
