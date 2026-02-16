# Phase 28: Input Normalization - Research

**Researched:** 2026-02-16
**Domain:** Input normalization for Planner Agent (GitHub issues, Observability incidents, CLI text)
**Confidence:** HIGH

## Summary

Phase 28 normalizes three input sources—GitHub issues (webhook or CLI), Observability (Sentry-derived) incidents, and operator CLI free text—into a single Planner input structure. No new external libraries are needed. The codebase already has: `build_sentry_issue_body` (Observability format), PyGithub for issues and repo tree, `_infer_repo_from_git`, and PlannerJob with full payload. CONTEXT.md locks the structure (hybrid goal+body, optional incident sections), detection strategy (label primary, Sentry heuristics fallback), and extraction depth.

**Primary recommendation:** Introduce a Pydantic `PlannerInput` model; add `planner/input.py` with normalizers for each source; wire into worker and CLI. Use PyGithub `get_contents("")` with recursive depth limit for optional repo tree.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | (existing) | PlannerInput, extraction models | Already used for Plan schema; type-safe normalization |
| PyGithub | (existing) | Issue fetch, repo tree | Already used for issues, get_contents, default_branch |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic BaseModel | dataclass | Pydantic enables validation, JSON export; dataclass simpler but less validation |
| PyGithub get_contents | GitHub API direct | PyGithub already in use; no gain from raw API |

## Architecture Patterns

### Recommended Project Structure

```
src/booty/planner/
├── input.py          # PlannerInput, normalizers, extractors
├── jobs.py           # (existing) PlannerJob
├── schema.py         # (existing) Plan
├── store.py          # (existing)
└── worker.py         # (existing) process_planner_job — consume PlannerInput
```

### Pattern 1: Source-Specific Normalizers

**What:** Entry point receives raw input; dispatcher selects normalizer; each normalizer returns same PlannerInput shape.
**When to use:** Multiple input formats feeding a single consumer.
**Example:**
```python
def normalize_github_issue(issue: dict, repo_info: dict | None) -> PlannerInput: ...
def normalize_cli_text(text: str, repo_info: dict | None) -> PlannerInput: ...
def normalize_from_job(job: PlannerJob) -> PlannerInput:
    issue = job.payload.get("issue", {})
    return normalize_github_issue(issue, {"owner": job.owner, "repo": job.repo})
```

### Pattern 2: Incident Detection (CONTEXT-locked)

**What:** Label primary (`agent:incident`), heuristics fallback (body markers `**Severity:**`, `**Sentry:**`, title `[severity]`).
**Reference:** `src/booty/github/issues.py` `build_sentry_issue_body` output structure.
**Markers:** `**Severity:**`, `**Environment:**`, `**Release:**`, `**Sentry:**`, `**Location:**`, `**Stack trace**`, `**Breadcrumbs:**`

### Anti-Patterns to Avoid

- **Over-extracting GitHub body:** CONTEXT says pass full body with length cap; don't extract sections.
- **Replacing incident body:** Extracted fields (location, sentry_url) are additive; keep full Sentry markdown in body.
- **Hand-rolling repo tree:** Use PyGithub `get_contents(path)`; limit depth to 2–3 levels.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Repo file tree | Custom Git API calls | PyGithub `repo.get_contents("", ref=default_branch)` | Already integrated; recursive for subdirs |
| Repo inference | Manual git config parsing | `_infer_repo_from_git(workspace)` | Already in cli.py |
| Issue fetch | Raw HTTP | PyGithub `repo.get_issue(n)` | Type-safe, consistent |

## Common Pitfalls

### Pitfall 1: Body Length Overflow
**What goes wrong:** Unbounded issue body blows LLM context.
**Why it happens:** Phase 29 consumes PlannerInput; long bodies waste tokens.
**How to avoid:** Apply trim cap per CONTEXT ("length cap; trim only").
**Warning signs:** Body > 8k chars without truncation.

### Pitfall 2: Misdetecting Incident vs Plain Issue
**What goes wrong:** Plain issue with "**Severity:**" in body wrongly treated as incident.
**Why it happens:** Heuristics too broad.
**How to avoid:** Require 2+ markers (e.g. `**Severity:**` AND `**Sentry:**`) for heuristics; label `agent:incident` overrides.
**Warning signs:** Single-marker detection.

### Pitfall 3: CLI --text Without Repo
**What goes wrong:** CLI text with no --repo and not in git dir fails or omits repo context.
**Why it happens:** CONTEXT: "Infer repo from cwd when in git repo; omit otherwise."
**How to avoid:** Explicitly handle: repo optional; when missing, PlannerInput has empty repo_context.
**Warning signs:** Requiring --repo for --text.

## Code Examples

### Sentry Body Markers (from build_sentry_issue_body)

```python
# Source: src/booty/github/issues.py
# Detection heuristics: body contains these markers
SENTRY_MARKERS = ["**Severity:**", "**Sentry:**", "**Location:**"]
# Optional: **Environment:**, **Release:**, **Stack trace**
```

### PyGithub Repo Tree (2 levels)

```python
def get_repo_tree_shallow(repo, ref: str, max_depth: int = 2) -> list[dict]:
    def _walk(path: str, depth: int) -> list:
        if depth > max_depth:
            return []
        contents = repo.get_contents(path or "", ref=ref)
        result = []
        for c in contents:
            result.append({"path": c.path, "type": c.type})
            if c.type == "dir" and depth < max_depth:
                result.extend(_walk(c.path, depth + 1))
        return result
    return _walk("", 0)
```

### source_type from Labels (CONTEXT)

```python
LABEL_TO_SOURCE = {"agent:incident": "incident", "bug": "bug", "enhancement": "feature_request"}
def derive_source_type(labels: list[str], body: str, title: str) -> str:
    for lbl in labels:
        if lbl in LABEL_TO_SOURCE:
            return LABEL_TO_SOURCE[lbl]
    if _looks_like_sentry_body(body) or _looks_like_sentry_title(title):
        return "incident"
    return "unknown"
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Worker uses only issue title | Worker consumes full PlannerInput (goal, body, labels, repo_context) | Phase 29 receives rich context |
| CLI --issue ignores body | CLI --issue normalizes full issue | Consistent with webhook path |
| No incident detection | Label + heuristics per CONTEXT | Observability issues recognized |

## Open Questions

1. **Exact body trim cap**
   - What we know: CONTEXT says "length cap; trim only"
   - What's unclear: 4k vs 8k vs 12k chars
   - Recommendation: 8k chars; configurable via planner config if needed later

2. **CLI goal/body split for --text**
   - What we know: "Split into goal (first part) + body (remainder)"
   - What's unclear: First line vs first sentence vs first paragraph
   - Recommendation: First line (until newline) as goal; remainder as body; if single line, all as goal, body empty

## Sources

### Primary (HIGH confidence)
- `src/booty/github/issues.py` — build_sentry_issue_body structure
- `src/booty/planner/jobs.py` — PlannerJob, payload shape
- `src/booty/planner/worker.py` — process_planner_job, current input use
- `src/booty/cli.py` — plan_issue, plan_text, _infer_repo_from_git
- `.planning/phases/28-input-normalization/28-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- PyGithub get_contents, default_branch — established usage in webhooks, cli, verifier

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in codebase
- Architecture: HIGH — patterns match existing planner/job flow
- Pitfalls: HIGH — derived from CONTEXT and codebase inspection

**Research date:** 2026-02-16
**Valid until:** 30 days (stable domain)
