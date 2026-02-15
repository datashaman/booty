# Phase 10: Import/Compile Detection - Context

**Gathered:** 2026-02-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Detect hallucinated imports (VERIFY-11) and compile failures (VERIFY-12) before or during the Verifier test run. Run full import + compile validation in the same environment as tests; fail fast where possible; surface failures in check output with annotations where applicable. Python only; diff limits apply to all files.

</domain>

<decisions>
## Implementation Decisions

### Import Resolution Scope

- **Full resolution** — Project + stdlib + installed third-party. Run in the same environment as tests.
- **Execution order:** setup_command → install_command → import + compile sweep → test_command. No separate lightweight import checker — that produces false confidence.
- **Dependency install failure** → Verifier fails immediately. Do not allow "imports look fine" without a successful environment build.
- **Conditional imports:** Always validate unconditional imports. Validate conditional imports only when the condition is true at runtime (Python version, platform markers). Treat `if TYPE_CHECKING:` imports as ignored.
- **Type stubs:** Ignore `.pyi` files for import-resolution check (runtime executability focus).
- **Dynamic imports:** Validate if statically analyzable (literal module string, e.g. `importlib.import_module("pkg.mod")`). Skip computed (formatting, vars, env). No partial evaluation.

### Failure Reporting Format

- **Annotations** for file-attributable failures: unresolved import, syntax error, compile error. Use when file:line available. Do NOT annotate: schema failures, diff limits, environment install failures (those remain check-level).
- **Cap:** 50 annotations per run. If exceeded: "Too many errors — showing first 50." Deduplicate identical errors. Severity: failure only (never warning).
- **Collect all, then fail** — Batch oracle; minimizes repair cycles. Stop collecting after 50 annotated failures; short-circuit remaining files.
- **Single check run** — One required gate. Sections in output: Schema, Limits, Imports, Compile, Tests.
- **Execution short-circuit order:** 1. Schema → 2. Limits → 3. Imports/Compile → 4. Tests.
- **Title pattern:** "Verifier failed — Import errors" | "Verifier failed — Compile errors" | "Verifier failed — Multiple failure classes" (never generic "Verification failed").
- **Summary pattern:** Counts per class, annotations shown (cap 50), whether tests ran or execution stopped early.

### Execution Order and setup_command

- **Order:** setup_command (optional) → install_command → import + compile sweep → test_command.
- **setup_command:** If present, always run first. Fail immediately if it errors; do not continue.
- **Compile capture:** Both setup_command stderr and import + compile sweep. Do not rely on test execution for syntax errors — tests are behavioral only.
- **setup_command failure reporting:** Annotate when file:line available (parse `File "path", line N` and `path:N:`). If localization fails → check-level summary. If both localized and non-localized → do both annotations + summary.
- **install_command:** New schema v1 field (e.g. `install_command: "pip install -r requirements.txt"`). Required for full import validation.
- **Agent PRs:** Missing install_command → fail with "Config required for agent PRs: install_command."
- **Non-agent PRs:** Missing install_command → skip import validation; run compile + tests. Summary note: "Imports: skipped (install_command not configured)". Not a failure.

### Edge Cases and Strictness

- **Files to parse:** Changed `.py` files only (added/modified/renamed). Exclude tests/** from max_loc_per_file enforcement only — still parse them for import/compile. Ignore deleted files.
- **__init__.py re-exports:** Treat as opaque. Require module/package imports successfully at runtime; do not statically validate re-exported symbols.
- **Optional deps:** Fail if import fails. Optionality not inferred from metadata. If truly optional, code must use lazy/guarded imports.
- **Python only** for import/compile sweep. Diff limits apply to all files. Cross-language validation is future scope.

### Claude's Discretion

- Exact py_compile/ast usage for compile sweep
- Parsing strategy for setup_command stderr (regex vs. structured)
- Annotation deduplication logic
- Exact wording for summary messages

</decisions>

<specifics>
## Specific Ideas

- "Annotations collapse detection → navigation → repair into one motion"
- "Batch oracle, not interactive debugger"
- "Tests are behavioral validation, not structural validation"
- "Generated code is still code; if you can localize it, you should"

</specifics>

<deferred>
## Deferred Ideas

- Type-check stage (mypy/pyright) for .pyi validation — future phase
- Cross-language validation — repo-specific test_command or later language plugins

</deferred>

---

*Phase: 10-import-compile-detection*
*Context gathered: 2026-02-15*
