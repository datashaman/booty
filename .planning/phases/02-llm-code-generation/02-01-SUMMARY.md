---
phase: 02-llm-code-generation
plan: 01
subsystem: foundation
tags: [dependencies, configuration, pydantic, models]
dependencies:
  requires: [01-02]
  provides: [llm-models, phase2-config, llm-dependencies]
  affects: [02-02, 02-03, 02-04, 02-05]
tech-stack:
  added: [magentic, PyGithub, anthropic, pathspec]
  patterns: [pydantic-models, structured-llm-output, field-descriptions]
key-files:
  created:
    - src/booty/llm/__init__.py
    - src/booty/llm/models.py
  modified:
    - pyproject.toml
    - src/booty/config.py
decisions:
  - name: "Use Pydantic BaseModel for all LLM structured outputs"
    rationale: "Type safety, validation, automatic retries with magentic"
    impact: "All LLM interactions must return Pydantic models"
  - name: "Conservative context window budget (180k tokens)"
    rationale: "Leave room for output, handle estimation variance per research"
    impact: "Code generation context selection must fit within budget"
  - name: "Full file generation model (not diffs)"
    rationale: "LLMs struggle with diff formats per 02-RESEARCH.md findings"
    impact: "FileChange.content contains complete file, not patches"
metrics:
  duration: "2 min"
  tasks: 2
  commits: 2
  files-created: 2
  files-modified: 2
  completed: 2026-02-14
---

# Phase 2 Plan 01: Dependencies, Config, and LLM Models Summary

**One-liner:** Installed magentic[anthropic], PyGithub, anthropic, pathspec; extended Settings with LLM/security config; created IssueAnalysis, FileChange, CodeGenerationPlan Pydantic models for type-safe LLM interactions.

## What Was Built

**Foundation for Phase 2 LLM Code Generation:**

1. **Dependencies installed** - All Phase 2 libraries now available:
   - `magentic[anthropic]` - Type-safe LLM decorator pattern with Pydantic integration
   - `PyGithub` - GitHub API operations (PR creation, issue fetching)
   - `anthropic` - Official Anthropic client for token counting
   - `pathspec` - Gitignore-style pattern matching for path restrictions

2. **Configuration extended** - Settings class enhanced with 5 new fields:
   - `ANTHROPIC_API_KEY` - Required API key for LLM calls
   - `LLM_MAX_TOKENS` - Output token limit (4096 default)
   - `LLM_MAX_CONTEXT_TOKENS` - Context window budget (180k conservative buffer)
   - `MAX_FILES_PER_ISSUE` - File count cap (10 default)
   - `RESTRICTED_PATHS` - Denylist patterns for security (workflows, env files, lockfiles)

3. **Pydantic models created** - Structured contracts for all LLM I/O:
   - `IssueAnalysis` - Issue understanding output (files, criteria, commit info)
   - `FileChange` - Single file modification (path, content, operation, explanation)
   - `CodeGenerationPlan` - Planning step (changes, approach, testing notes)

## Technical Implementation

### Dependency Management
- Added 4 new dependencies to `pyproject.toml` dependencies array
- Used `magentic[anthropic]` extra to include Anthropic-specific support
- All dependencies verified importable via test imports

### Configuration Extension
- Extended Settings class with Phase 2 section
- All new fields properly typed (str, int, str defaults)
- ANTHROPIC_API_KEY required field (no default) for explicit configuration
- Conservative token limits based on 02-RESEARCH.md recommendations

### Pydantic Model Design
- All models inherit from `pydantic.BaseModel`
- Every field has `Field()` with description for LLM clarity
- `FileChange.operation` uses `Literal["create", "modify", "delete"]` for type safety
- Default values where appropriate (files_to_delete, commit_scope)
- Models validate at runtime (tested with invalid/valid data)

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

### 1. Conservative Context Window Budget (180k tokens)
**Context:** Claude Sonnet 4 has 200k context window, but token counting is estimate-based

**Decision:** Set `LLM_MAX_CONTEXT_TOKENS` to 180k (90% of max)

**Rationale:**
- 02-RESEARCH.md identified token counting accuracy concerns
- Prompt caching may affect actual usage vs. estimates
- 20k buffer provides safety margin for estimation variance
- Follows research recommendation for conservative budgets

**Impact:** Code generation context selection must account for buffer, reducing available space but preventing overflow errors

### 2. Full File Content in FileChange Model
**Context:** Code generation can use diffs or full file replacement

**Decision:** `FileChange.content` field stores complete file content, not diffs

**Rationale:**
- 02-RESEARCH.md: "LLMs struggle with diff formats, full files work better"
- Higher success rate for LLM code generation
- Simpler validation (can parse entire file with ast.parse)
- Avoids patch application failures

**Impact:** All code generation prompts must request full file content, not patches

### 3. Pydantic BaseModel for All LLM Outputs
**Context:** LLM responses could be parsed as strings or structured data

**Decision:** All LLM interactions return Pydantic models, never plain strings

**Rationale:**
- Type safety - Field types enforced at runtime
- Automatic validation - Bad LLM outputs rejected immediately
- magentic integration - Automatic retries when validation fails
- Documentation - Field descriptions guide LLM output format

**Impact:** All future @prompt decorators must specify return type as Pydantic model

## Integration Points

### For 02-02 (Path Security)
- `Settings.RESTRICTED_PATHS` provides denylist patterns
- Models available for import in validation logic
- `FileChange.path` field is the target for security checks

### For 02-03 (Git Operations)
- `IssueAnalysis.commit_type` and `commit_scope` drive conventional commits
- `FileChange` models provide file list for git add operations
- `IssueAnalysis.summary` used for commit message titles

### For 02-04 (LLM Prompts)
- `IssueAnalysis`, `FileChange`, `CodeGenerationPlan` are return types for @prompt functions
- Token budget settings (`LLM_MAX_TOKENS`, `LLM_MAX_CONTEXT_TOKENS`) configure magentic
- `ANTHROPIC_API_KEY` enables LLM calls

### For 02-05 (Orchestrator)
- All models imported for type annotations in process_job pipeline
- Settings fields available for configuration of LLM calls
- Dependencies installed enable magentic/PyGithub usage

## Verification Results

All verification criteria passed:

- ✅ `pip install -e ".[dev]"` succeeds
- ✅ `import magentic, github, anthropic, pathspec` succeeds
- ✅ Settings has ANTHROPIC_API_KEY, LLM_MAX_TOKENS, LLM_MAX_CONTEXT_TOKENS, MAX_FILES_PER_ISSUE, RESTRICTED_PATHS (5/5 fields)
- ✅ IssueAnalysis, FileChange, CodeGenerationPlan importable from booty.llm.models
- ✅ Models validate correctly (reject invalid Literal values, accept valid data)

## Next Phase Readiness

**Phase 2 foundation is complete.** All downstream plans (02-02 through 02-05) can now:
- Import structured LLM models for type-safe interactions
- Access Phase 2 configuration settings (API keys, token limits, path restrictions)
- Use installed dependencies (magentic, PyGithub, anthropic, pathspec)

**No blockers for next plan (02-02).**

**Recommended next steps:**
1. Plan 02-02: Implement path security validation using Settings.RESTRICTED_PATHS
2. Plan 02-03: Build git operations using IssueAnalysis commit metadata
3. Plan 02-04: Create @prompt functions returning these Pydantic models
4. Plan 02-05: Wire everything into process_job orchestrator

## Task Breakdown

### Task 1: Install Phase 2 dependencies and extend config
**Duration:** ~1 min
**Commit:** 4125c12

**What was done:**
- Added 4 dependencies to pyproject.toml (magentic[anthropic], PyGithub, anthropic, pathspec)
- Ran `pip install -e ".[dev]"` to install new packages
- Extended Settings class with 5 new Phase 2 fields
- Added "# Phase 2: LLM Code Generation" section comment for clarity

**Verification:**
- All dependencies imported successfully
- Settings class loads without errors
- New fields have correct types and defaults

### Task 2: Create Pydantic models for LLM structured outputs
**Duration:** ~1 min
**Commit:** dd50c95

**What was done:**
- Created src/booty/llm/__init__.py package marker
- Created src/booty/llm/models.py with 3 Pydantic models:
  - IssueAnalysis (8 fields with descriptions)
  - FileChange (4 fields with Literal type for operation)
  - CodeGenerationPlan (3 fields)
- All fields documented with Field(description=...) for LLM clarity

**Verification:**
- All models importable from booty.llm.models
- FileChange instantiates correctly with valid data
- FileChange rejects invalid operation values (tested with "invalid" → ValidationError)

## Files Changed

### Created
- `src/booty/llm/__init__.py` - Package marker for LLM integration module
- `src/booty/llm/models.py` - Pydantic models for structured LLM outputs (46 lines)

### Modified
- `pyproject.toml` - Added 4 Phase 2 dependencies
- `src/booty/config.py` - Added 5 Phase 2 settings fields

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 4125c12 | chore | Install Phase 2 dependencies and extend config |
| dd50c95 | feat | Create Pydantic models for LLM structured outputs |

---
*Phase 2 foundation complete. All downstream LLM plans now have structured models, configuration, and dependencies available.*
