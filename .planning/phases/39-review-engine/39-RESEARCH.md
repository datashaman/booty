# Phase 39: Review Engine - Research

**Researched:** 2026-02-17
**Domain:** LLM-based code review with structured output
**Confidence:** HIGH

## Summary

Phase 39 implements the Review Engine: a diff-focused LLM prompt producing structured output (decision + 6 category grades + findings). CONTEXT.md locks the rubric structure, block_on mapping, and comment format. Research focuses on Magentic integration (already in stack), prompt design for diff-based review, and output schema patterns.

The codebase already uses Magentic with `@prompt` and Pydantic return types (planner, code_gen). Same pattern applies: define Pydantic model as return type, Magentic produces structured JSON. No new LLM libraries needed.

**Primary recommendation:** Use Magentic `@prompt` with a Pydantic `ReviewResult` model; provide unified diff + PR metadata; map block_on config to which categories block; format comment from ReviewResult using CONTEXT.md spec.

## Standard Stack

### Core (already in use)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| magentic[anthropic] | installed | LLM calls with structured output | Already used by Planner, code_gen; no new dep |
| pydantic | installed | Output schema validation | Magentic return types; nested models |
| anthropic | installed | Claude API | Via magentic |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Magentic | raw anthropic SDK | Magentic gives @prompt + structured output; codebase standard |
| Pydantic nested | dict[str, Any] | Validation fails fast; schema documents output |

## Architecture Patterns

### Recommended Project Structure
```
src/booty/reviewer/
├── config.py        # ReviewerConfig (exists)
├── job.py          # ReviewerJob (exists)
├── queue.py        # ReviewerQueue (exists)
├── runner.py       # process_reviewer_job — extend with LLM call
├── engine.py       # NEW: run_review(diff, config) -> ReviewResult
├── schema.py       # NEW: ReviewResult, CategoryResult, Finding
└── prompts.py      # NEW: Magentic @prompt -> ReviewResult
```

### Pattern: Magentic + Pydantic
**What:** Decorated function returns Pydantic model; Magentic infers JSON schema from type hints
**Example:** (from planner/generation.py)
```python
@prompt("""...""", max_retries=3)
def _generate_plan_impl(goal: str, body: str, repo_tree: str) -> Plan:
    ...
```
**Use:** Same pattern for `run_review(diff, pr_meta, block_on) -> ReviewResult`

### Pattern: block_on → blocking categories
**What:** Config block_on = ["overengineering", "poor_tests"] maps to which category grades trigger BLOCKED
**Mapping:** overengineering → Overengineering, poor_tests → Tests, duplication → Duplication, architectural_regression → Architectural drift
**Logic:** Only enabled block_on categories can block; Maintainability and Naming/API never block

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM API calls | Raw requests | Magentic | Retries, structured output, model config |
| Output parsing | Regex on raw text | Pydantic return type | Validation, nested structure |
| Diff fetching | Manual patch assembly | PyGithub compare | repo.compare(base, head) returns files + patch |

## Common Pitfalls

### Pitfall 1: Diff too large
**What goes wrong:** PR with 50 files blows token limit; LLM truncates or errors
**Why it happens:** Full unified diff can exceed 100k tokens for large PRs
**How to avoid:** Truncate or sample; CONTEXT says "unified diff" — cap total chars (e.g. 80k), prefer changed lines over full files
**Warning signs:** RateLimitError, token budget exceeded

### Pitfall 2: block_on vs category mismatch
**What goes wrong:** block_on has typo or unknown value; blocks anyway or never blocks
**Why it happens:** block_on validated at config load; engine must map string → category
**How to avoid:** Explicit map `BLOCK_ON_TO_CATEGORY = {"overengineering": "Overengineering", ...}`; only these 4 keys; unknown block_on ignored
**Warning signs:** Config allows any string; mapping incomplete

### Pitfall 3: Comment format drift
**What goes wrong:** Comment structure doesn't match CONTEXT.md; parsing or display breaks
**Why it happens:** Ad-hoc string building
**How to avoid:** Single `format_reviewer_comment(result: ReviewResult) -> str` function; structure matches CONTEXT exactly (header, rationale, sections in order)
**Warning signs:** Inline f-strings scattered in runner

## Code Examples

### Magentic prompt with nested Pydantic (existing pattern)
```python
# From planner/generation.py — return type drives schema
@prompt("""...""", max_retries=3)
def _generate_plan_impl(goal: str, body: str, repo_tree: str) -> Plan:
    ...
```

### PyGithub compare for diff
```python
# repo.compare(base_sha, head_sha) returns Compare object
compare = repo.compare(base_sha, head_sha)
for f in compare.files:
    # f.filename, f.patch (unified diff), f.status
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Raw API + manual JSON parse | Magentic + Pydantic | Structured output, retries built-in |
| Full file contents in prompt | Unified diff only | Token efficient; CONTEXT locks this |

## Open Questions

None — CONTEXT.md provides sufficient constraints.

## Sources

### Primary (HIGH confidence)
- Codebase: magentic usage in planner/generation.py, llm/prompts.py
- Codebase: ReviewerConfig, runner.py stub, post_reviewer_comment

### Secondary
- PyGithub Compare: standard for diff retrieval

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing magentic, pydantic in use
- Architecture: HIGH — CONTEXT locks structure; patterns clear
- Pitfalls: MEDIUM — token limits, mapping logic

**Research date:** 2026-02-17
**Valid until:** 30 days
