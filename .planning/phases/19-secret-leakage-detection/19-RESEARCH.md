# Phase 19: Secret Leakage Detection - Research

**Researched:** 2026-02-16
**Domain:** Secret scanning (gitleaks, trufflehog), GitHub Checks API annotations
**Confidence:** HIGH

## Summary

Phase 19 adds diff-based secret scanning to the booty/security check. The standard approach is gitleaks (preferred per CONTEXT.md) with trufflehog as fallback. Gitleaks supports `stdin` mode to scan `git diff` output, enabling changed-files-only scanning. The existing `edit_check_run` already supports annotations (path, start_line, end_line, annotation_level, message, title) and GitHub limits to 50 per request. Phase 18 delivers the check lifecycle; Phase 19 wires the scanner into it.

**Primary recommendation:** Use `git diff base_sha..head_sha | gitleaks stdin --report-format json`. Clone repo at head_sha, run diff against base from payload, parse JSON, convert to annotations (cap 50), FAIL check with title "Security failed — secret detected".

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| gitleaks | v8.25+ | Secret detection in git/diff | Industry standard, regex+entropy, JSON/SARIF output |
| trufflehog | v3.x | Fallback scanner | Alternative when gitleaks missing |

### Supporting

| Item | Purpose | When to Use |
|------|---------|-------------|
| git diff | Changed content only | PR merge-base..head diff |
| PyGithub edit_check_run | Check output + annotations | Already in checks.py (Phase 10) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| gitleaks stdin | gitleaks dir on changed files | stdin simpler: one pipe, no file filtering |
| gitleaks | detect-secrets, Semgrep | gitleaks preferred per roadmap; detect-secrets less maintained |

**Installation:**
```bash
brew install gitleaks
# or: download from https://github.com/gitleaks/gitleaks/releases
```

## Architecture Patterns

### Recommended Structure

```
src/booty/security/
├── runner.py         # process_security_job (Phase 18) — extend with scan
├── scanner.py        # NEW: run_gitleaks, parse findings, build annotations
├── job.py            # SecurityJob (add base_sha or extract from payload)
└── queue.py          # SecurityQueue
```

### Pattern 1: Diff-based scan

**What:** Pipe `git diff base..head` to `gitleaks stdin`.
**When:** PR security scan — scan only changed lines.
**Example:**
```bash
cd /path/to/clone
git diff base_sha..head_sha | gitleaks detect --source stdin --report-format json --no-git
```
Note: gitleaks v8 uses `gitleaks git` or `gitleaks dir` or `gitleaks stdin`. Stdin: `cat file | gitleaks detect --source stdin` or similar. Verify CLI: `gitleaks stdin --help`.

From gitleaks README: "You can also stream data to gitleaks with the stdin command. Example: `cat some_file | gitleaks -v stdin`"

So: `git diff base..head | gitleaks stdin -v` — exit code 1 when leaks found.

**Output:** Findings to stdout (or --report-path json). Parse for File, StartLine, Secret, RuleID.

### Pattern 2: GitHub annotations from findings

**What:** Convert gitleaks JSON findings to Checks API annotations. Limit 50.
**Structure:** `{path, start_line, end_line, annotation_level: "failure", message, title}`

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secret regex rules | Custom regex engine | gitleaks built-in rules | 200+ rules, entropy, allowlists |
| Git diff parsing | Manual parsing | `git diff` + gitleaks stdin | gitleaks understands diff format |
| Lockfile exclusions | Custom path filter | gitleaks [allowlist] paths | Default config already excludes package-lock.json, etc. |

## Common Pitfalls

### Pitfall 1: Full-repo scan in CI
**What goes wrong:** Scanning entire history/repo → slow, hits 60s limit.
**Why:** Using `gitleaks git` without log-opts or scanning dir instead of diff.
**How to avoid:** Use `git diff base..head | gitleaks stdin` — only changed content.
**Warning signs:** Scan >30s, many unchanged files in output.

### Pitfall 2: Annotation limit exceeded
**What goes wrong:** GitHub rejects output with >50 annotations.
**Why:** Large PR with many secrets.
**How to avoid:** Cap at 50, sort by severity/confidence, add "and N more" to summary.
**Warning signs:** 50+ findings, API 422.

### Pitfall 3: Scanner binary missing
**What goes wrong:** subprocess fails, check never completes.
**Why:** gitleaks/trufflehog not installed in runtime.
**How to avoid:** Try gitleaks first; if missing, try trufflehog; if both missing, FAIL with clear message "Secret scanner not found".
**Warning signs:** FileNotFoundError, exit code 127.

## Code Examples

### Gitleaks stdin (from README)
```bash
cat some_file | gitleaks stdin
# or
git diff base..head | gitleaks stdin --no-banner
```

### Gitleaks JSON report
```bash
gitleaks detect --source git --log-opts="base..head" --report-format json --report-path findings.json
# For stdin:
git diff base..head | gitleaks detect --source stdin --report-format json --report-path -
```

### Annotation format (from checks.py docstring)
```python
output={
    "title": "Security failed — secret detected",
    "summary": "3 secrets in 2 files",
    "annotations": [
        {"path": "src/config.py", "start_line": 12, "end_line": 12,
         "annotation_level": "failure", "message": "API key detected", "title": "Secret"}
    ]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| detect/protect commands | git/dir/stdin | v8.19 | Same functionality, clearer CLI |
| [allowlist] | [[allowlists]] | v8.21 | Multi-allowlist per rule |
| Single allowlist | [[allowlists]] with targetRules | v8.25 | Shared allowlists |

## Open Questions

1. **gitleaks stdin exact CLI**
   - What we know: `gitleaks stdin` accepts piped input; exit 1 on findings
   - What's unclear: Exact flags for JSON output from stdin
   - Recommendation: Use `--report-path findings.json` and read file; or parse human output. Verify with `gitleaks stdin --help`.

2. **Workspace for Security**
   - What we know: Verifier clones via prepare_verification_workspace
   - What's unclear: Reuse same workspace prep or lighter clone
   - Recommendation: Add prepare_security_workspace (or reuse) — clone at head_sha, run git diff (base from payload) in that clone.

## Sources

### Primary (HIGH confidence)
- gitleaks GitHub README — stdin, dir, git commands; config allowlist
- GitHub Checks API — output.annotations structure
- booty checks.py — edit_check_run annotations support (Phase 10)

### Secondary (MEDIUM confidence)
- gitleaks default config (allowlist paths for lockfiles)
- WebSearch: diff-only scanning patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — gitleaks well-documented
- Architecture: HIGH — matches Verifier patterns
- Pitfalls: HIGH — known CI scanner issues

**Research date:** 2026-02-16
**Valid until:** 2026-03-16
