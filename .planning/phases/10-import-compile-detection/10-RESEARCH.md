# Phase 10: Import/Compile Detection - Research

**Researched:** 2026-02-15
**Domain:** Python AST/compile validation, GitHub Checks API annotations, Verifier pipeline
**Confidence:** HIGH

## Summary

Phase 10 adds import resolution and compile validation to the Verifier before/during test runs. The implementation uses Python stdlib (ast, py_compile) for syntax/compile checks, runtime import validation in the workspace environment, and GitHub Checks API annotations for file:line reporting.

**Key decisions from CONTEXT.md are locked:** Full resolution in test env, setup_command → install_command → import+compile sweep → test_command, annotations for file-attributable failures (cap 50), single check run with sections.

**Primary recommendation:** Use ast + py_compile for compile sweep; run import validation via subprocess Python script in workspace (same env as tests); add install_command to BootyConfigV1; extend edit_check_run to pass annotations in output dict.

## Standard Stack

### Core (stdlib only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ast | 3.x | Parse .py files, extract imports | Stdlib, handles all Python syntax |
| py_compile | 3.x | Compile sweep, SyntaxError capture | Stdlib, doraise=True raises PyCompileError |
| importlib | 3.x | Runtime import validation | Stdlib, import_module() for resolution |

### Existing Codebase

| Module | Purpose | Reuse |
|--------|---------|-------|
| booty/test_generation/validator.py | extract_imports(tree), ast.parse | Adapt for changed files; different validation (runtime vs static) |
| booty/code_gen/validator.py | ast.parse for syntax check | Pattern for compile validation |
| booty/test_runner/executor.py | execute_tests(command, timeout, path) | Use for setup_command, install_command, import script |
| booty/github/checks.py | edit_check_run(output=...) | Extend output to include annotations[] |
| booty/verifier/limits.py | get_pr_diff_stats, check_diff_limits | get changed .py files from PR |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| py_compile | compile(source, file, 'exec') | compile() gives SyntaxError with lineno/msg directly; py_compile needs doraise |
| Static import check (metadata) | Runtime importlib | CONTEXT locks "full resolution"; static produces false confidence |
| Custom annotation API | GitHub output.annotations | Checks API supports annotations in output; 50 per request limit |

## Architecture Patterns

### Execution Order (from CONTEXT)

```
1. setup_command (optional) → fail immediately on error
2. install_command (new schema field) → fail on error
3. import + compile sweep (changed .py files only)
4. test_command
```

### Pattern 1: Compile Sweep with py_compile

**What:** Use py_compile.compile(file, doraise=True) to catch syntax errors; PyCompileError has .file, .msg attributes. SyntaxError (from compile()) has .lineno, .msg, .text.

**Source:** Python 3.14 py_compile docs; PyCompileError wraps SyntaxError info.

```python
import py_compile
try:
    py_compile.compile(str(path), doraise=True)
except py_compile.PyCompileError as e:
    # e.msg, e.file; SyntaxError also has e.lineno
    # Use traceback or e.exc_value if PyCompileError wraps SyntaxError
```

**Note:** PyCompileError.exc_value may be the underlying SyntaxError with lineno. Verify at implementation.

### Pattern 2: Import Extraction from AST

**What:** Walk AST to get Import/ImportFrom nodes. Skip TYPE_CHECKING guards (CONTEXT: treat as ignored). Skip conditional imports when condition is false (platform, version).

**Source:** Existing booty/test_generation/validator.py extract_imports().

```python
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            root = alias.name.split(".")[0]
            imports.append((root, node.lineno))  # keep line for annotation
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.append((node.module.split(".")[0], node.lineno))
```

**TYPE_CHECKING:** Check parent: if inside `if False:` or `if TYPE_CHECKING:` block, skip. ast.NodeVisitor can inspect get_source_segment or parent chain.

### Pattern 3: GitHub Check Run Annotations

**What:** output dict includes annotations array. Each: path, start_line, end_line, annotation_level ("failure"), message, title.

**Source:** GitHub REST API docs (create check run, update check run).

```python
output = {
    "title": "Verifier failed — Import errors",
    "summary": "3 import errors, 0 compile errors. Tests not run.",
    "text": "...",
    "annotations": [
        {
            "path": "src/foo/bar.py",
            "start_line": 12,
            "end_line": 12,
            "annotation_level": "failure",
            "title": "Unresolved import",
            "message": "No module named 'hallucinated'",
        }
    ],
}
# Cap 50; deduplicate; if exceeded: "Too many errors — showing first 50."
edit_check_run(check_run, output=output)
```

### Anti-Patterns to Avoid

- **Static-only import check:** CONTEXT requires runtime in test env. Don't rely on pyproject/requirements parsing alone.
- **Separate lightweight import checker:** CONTEXT: "No separate lightweight import checker — that produces false confidence."
- **Annotating schema/limits failures:** CONTEXT: Annotations for file-attributable failures only. Schema, limits, env install → check-level summary.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python parsing | Regex for imports | ast.parse | Handles continuations, comments, edge cases |
| Syntax validation | Custom parser | py_compile or compile() | Stdlib catches all SyntaxError cases |
| Traceback parsing | Complex regex | re for `File "path", line N` and `path:N:` | CONTEXT: parse setup_command stderr |
| Import resolution | Static module scan | importlib.import_module in workspace subprocess | Same env as tests; full resolution |

## Common Pitfalls

### Pitfall 1: Running Import Check in Booty Process

**What goes wrong:** Booty's venv != workspace venv. importlib.import_module in Booty sees Booty's deps, not PR's.

**Why it happens:** Assuming same process = same environment.

**How to avoid:** Run import validation as a subprocess in workspace (e.g. `python -c "..."` or helper script) so it uses workspace cwd and site-packages.

### Pitfall 2: Annotation Limit 50

**What goes wrong:** Sending >50 annotations in one output causes API rejection or truncation.

**How to avoid:** Cap at 50, deduplicate identical (path, line, message), add summary "Too many errors — showing first 50." when truncated.

### Pitfall 3: setup_command stderr Format Variance

**What goes wrong:** Tracebacks vary: `File "path", line N`, `  File "path", line N`, `path:N:`, different quoting.

**How to avoid:** Use regex for both patterns; if parse fails, fall back to check-level summary. CONTEXT: "If localization fails → check-level summary."

### Pitfall 4: install_command Missing for Agent PRs

**What goes wrong:** Agent PR without install_command → cannot resolve third-party imports; false failures.

**How to avoid:** CONTEXT: "Agent PRs: Missing install_command → fail with 'Config required for agent PRs: install_command.'" Enforce before import sweep.

## Code Examples

### PyCompileError and lineno

```python
# py_compile.compile raises PyCompileError; attr exc_value may hold SyntaxError
import py_compile
try:
    py_compile.compile("bad.py", doraise=True)
except py_compile.PyCompileError as e:
    # Python docs: PyCompileError has msg; may have exc_value.msg, exc_value.lineno
    se = getattr(e, 'exc_value', e)
    lineno = getattr(se, 'lineno', None) or 0
```

### execute_command Helper

```python
# Generalize execute_tests to run arbitrary command; reuse TestResult pattern
async def execute_command(cmd: str, timeout: int, cwd: Path) -> TestResult:
    # Same as execute_tests but generic command
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Regex import extraction | ast.parse + walk | Handles multiline, from X import (a, b) |
| Rely on test run for syntax | Explicit compile sweep | CONTEXT: "Tests are behavioral only" |
| Check output without annotations | Annotations for file:line | Collapse detect → navigate → repair |

**Deprecated/outdated:**
- Relying on pytest/tox to catch import errors: Verifier should fail fast before test discovery.

## Open Questions

1. **PyCompileError attributes:** Confirm whether exc_value/lineno available on PyCompileError for annotation. Fallback: use 0 or file-level.
2. **TYPE_CHECKING detection:** ast.NodeVisitor: need parent to see `if typing.TYPE_CHECKING` or `if False`. Consider ast.get_source_segment or symbol resolution.
3. **install_command field:** Add to BootyConfigV1. BootyConfig (v0) has no install — v0 repos unaffected.

## Sources

### Primary (HIGH confidence)
- Python 3.14 py_compile docs
- GitHub REST API checks/runs (output.annotations)
- booty/test_generation/validator.py — extract_imports pattern
- booty/verifier/runner.py — current flow
- 10-CONTEXT.md — locked decisions

### Secondary (MEDIUM confidence)
- WebSearch: PyCompileError, SyntaxError lineno
- WebSearch: GitHub Checks annotations format

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib + existing codebase
- Architecture: HIGH — CONTEXT locks most decisions
- Pitfalls: HIGH — subprocess env, annotation cap well documented

**Research date:** 2026-02-15
**Valid until:** 30 days (stable Python/GitHub APIs)
