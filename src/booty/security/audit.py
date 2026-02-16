"""Dependency vulnerability auditing — lockfile detection and per-ecosystem audit."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from booty.test_runner.config import SecurityConfig

LOCKFILE_PATTERNS: dict[str, list[str]] = {
    "python": [
        "**/requirements*.txt",
        "**/pyproject.toml",
        "**/poetry.lock",
        "**/Pipfile.lock",
        "**/uv.lock",
    ],
    "node": [
        "**/package-lock.json",
        "**/yarn.lock",
        "**/pnpm-lock.yaml",
    ],
    "php": ["**/composer.lock"],
    "rust": ["**/Cargo.lock"],
}

# Lockfile basename -> is true lockfile (vs manifest)
PYTHON_LOCKFILES = {"poetry.lock", "Pipfile.lock", "uv.lock"}

TOOL_BY_ECOSYSTEM: dict[str, dict[str, str]] = {
    "node": {
        "package-lock.json": "npm",
        "yarn.lock": "yarn",
        "pnpm-lock.yaml": "pnpm",
    },
    "python": {"*": "pip-audit"},
    "php": {"composer.lock": "composer"},
    "rust": {"Cargo.lock": "cargo"},
}


@dataclass
class AuditResult:
    """Result of dependency audit across all ecosystems."""

    ok: bool
    findings: list[dict]
    errors: list[str]
    summary_by_ecosystem: dict[str, str]
    worst_severity: str | None  # "critical" | "high" | "medium" | "low" | None


def discover_lockfiles(workspace_path: Path) -> list[tuple[str, Path]]:
    """Discover lockfiles and manifests in workspace.

    Returns [(ecosystem, path), ...] for each found file.
    Deduplicates by content hash (identical files count as one).
    Sorted by (ecosystem, path) for deterministic order.
    """
    workspace = Path(workspace_path).resolve()
    if not workspace.exists() or not workspace.is_dir():
        return []

    seen_hashes: set[str] = set()
    results: list[tuple[str, Path]] = []

    for ecosystem, patterns in LOCKFILE_PATTERNS.items():
        for pattern in patterns:
            for path in workspace.rglob(pattern.replace("**/", "")):
                if not path.is_file():
                    continue
                try:
                    content = path.read_bytes()
                except OSError:
                    continue
                h = hashlib.sha256(content).hexdigest()
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)

                # Map path to ecosystem
                base = path.name
                if ecosystem == "python":
                    if base in PYTHON_LOCKFILES:
                        results.append((ecosystem, path))
                    elif base == "pyproject.toml" or base.startswith("requirements") and base.endswith(".txt"):
                        results.append((ecosystem, path))
                elif ecosystem == "node":
                    if base in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml"):
                        results.append((ecosystem, path))
                elif ecosystem == "php" and base == "composer.lock":
                    results.append((ecosystem, path))
                elif ecosystem == "rust" and base == "Cargo.lock":
                    results.append((ecosystem, path))

    # Dedupe Python: prefer lockfile over manifest per directory
    results = _dedupe_python_targets(results)

    results.sort(key=lambda x: (x[0], str(x[1])))
    return results


def _dedupe_python_targets(
    items: list[tuple[str, Path]],
) -> list[tuple[str, Path]]:
    """For Python: one audit per directory; prefer lockfile over manifest."""
    by_dir: dict[Path, Path] = {}
    for ecosystem, path in items:
        if ecosystem != "python":
            continue
        parent = path.parent
        base = path.name
        existing = by_dir.get(parent)
        if existing is None:
            by_dir[parent] = path
        else:
            existing_base = existing.name
            # Prefer lockfile over manifest
            if base in PYTHON_LOCKFILES and existing_base not in PYTHON_LOCKFILES:
                by_dir[parent] = path
            elif base in PYTHON_LOCKFILES and existing_base in PYTHON_LOCKFILES:
                order = ("poetry.lock", "Pipfile.lock", "uv.lock")
                if order.index(base) < order.index(existing_base):
                    by_dir[parent] = path

    # Rebuild: Python uses by_dir (one per dir), others pass through
    out: list[tuple[str, Path]] = []
    for ecosystem, path in items:
        if ecosystem != "python":
            out.append((ecosystem, path))
    for path in by_dir.values():
        out.append(("python", path))
    return out


def _run_python_audit(
    path: Path,
    fail_severity: str,
) -> tuple[list[dict], list[str], str]:
    """Run pip-audit for Python. Returns (findings, errors, summary)."""
    findings: list[dict] = []
    errors: list[str] = []
    bin_name = "pip-audit"
    if shutil.which(bin_name) is None:
        errors.append(
            "pip-audit not found — install to enable Python dependency audit"
        )
        return findings, errors, "pip-audit not installed"

    cwd = path.parent
    args = [bin_name, "-f", "json"]
    if path.name in PYTHON_LOCKFILES:
        args.extend(["--locked"])
    elif path.name.startswith("requirements") and path.name.endswith(".txt"):
        args.extend(["-r", str(path)])
    else:
        # pyproject.toml
        args.append(".")

    for attempt in range(3):
        try:
            proc = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                timeout=30,
                text=True,
            )
            break
        except subprocess.TimeoutExpired:
            if attempt == 2:
                errors.append("pip-audit timed out")
                return findings, errors, "timed out"
            time.sleep(2**attempt)
        except Exception as e:
            if attempt == 2:
                errors.append(f"pip-audit failed: {e}")
                return findings, errors, str(e)
            time.sleep(2**attempt)
    else:
        return findings, errors, "unknown"

    if proc.returncode not in (0, 1):
        stderr = proc.stderr or ""
        errors.append(f"pip-audit error: {stderr.strip() or 'unknown'}")
        return findings, errors, "error"

    # Parse JSON; pip-audit vulns lack severity — treat as high when present
    if proc.stdout:
        try:
            data = json.loads(proc.stdout)
            if isinstance(data, list):
                for pkg in data:
                    if isinstance(pkg, dict) and "vulns" in pkg:
                        for v in pkg["vulns"]:
                            if isinstance(v, dict):
                                vuln_id = v.get("id") or v.get("name") or "unknown"
                                findings.append({
                                    "ecosystem": "python",
                                    "path": str(path),
                                    "package": pkg.get("name", "?"),
                                    "severity": "high",  # conservative per RESEARCH
                                    "cve_id": vuln_id,
                                })
        except json.JSONDecodeError:
            pass

    summary = f"{len(findings)} high" if findings else "passed"
    return findings, errors, summary


def _run_node_audit(
    path: Path,
    tool: str,
    fail_severity: str,
) -> tuple[list[dict], list[str], str]:
    """Run npm/yarn/pnpm audit. Returns (findings, errors, summary)."""
    findings: list[dict] = []
    errors: list[str] = []
    bin_name = tool
    if shutil.which(bin_name) is None:
        msg = f"{tool} not found — install to enable Node dependency audit"
        errors.append(msg)
        return findings, errors, "tool not installed"

    cwd = path.parent
    args = [bin_name, "audit", "--json"]
    if tool == "npm":
        args.extend(["--audit-level", fail_severity])

    for attempt in range(3):
        try:
            proc = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                timeout=30,
                text=True,
            )
            break
        except subprocess.TimeoutExpired:
            if attempt == 2:
                errors.append(f"{tool} audit timed out")
                return findings, errors, "timed out"
            time.sleep(2**attempt)
        except Exception as e:
            if attempt == 2:
                errors.append(f"{tool} audit failed: {e}")
                return findings, errors, str(e)
            time.sleep(2**attempt)
    else:
        return findings, errors, "unknown"

    # Parse metadata.vulnerabilities
    if proc.stdout:
        try:
            data = json.loads(proc.stdout)
            meta = data.get("metadata", {}).get("vulnerabilities", {})
            total = meta.get("critical", 0) + meta.get("high", 0)
            if fail_severity in ("high", "critical"):
                total += meta.get("moderate", 0) if fail_severity == "medium" else 0
            high = meta.get("high", 0)
            critical = meta.get("critical", 0)
            if high or critical:
                for _ in range(min(critical, 50)):
                    findings.append({
                        "ecosystem": "node",
                        "path": str(path),
                        "package": "?",
                        "severity": "critical",
                        "cve_id": "",
                    })
                for _ in range(min(high, 50)):
                    findings.append({
                        "ecosystem": "node",
                        "path": str(path),
                        "package": "?",
                        "severity": "high",
                        "cve_id": "",
                    })
            summary = f"{critical} critical, {high} high" if (high or critical) else "passed"
        except json.JSONDecodeError:
            summary = "parse error"
            errors.append(f"{tool} audit JSON parse failed")
    else:
        summary = "error"

    return findings, errors, summary


def _run_composer_audit(
    path: Path,
    fail_severity: str,
) -> tuple[list[dict], list[str], str]:
    """Run composer audit. Returns (findings, errors, summary)."""
    findings: list[dict] = []
    errors: list[str] = []
    bin_name = "composer"
    if shutil.which(bin_name) is None:
        errors.append(
            "composer not found — install to enable PHP dependency audit"
        )
        return findings, errors, "composer not installed"

    cwd = path.parent
    args = [bin_name, "audit", "--format=json", "--no-interaction"]

    for attempt in range(3):
        try:
            proc = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                timeout=30,
                text=True,
            )
            break
        except subprocess.TimeoutExpired:
            if attempt == 2:
                errors.append("composer audit timed out")
                return findings, errors, "timed out"
            time.sleep(2**attempt)
        except Exception as e:
            if attempt == 2:
                errors.append(f"composer audit failed: {e}")
                return findings, errors, str(e)
            time.sleep(2**attempt)
    else:
        return findings, errors, "unknown"

    # Exit 1=vulns, 2=abandoned, 3=both
    if proc.returncode in (1, 3) and proc.stdout:
        try:
            data = json.loads(proc.stdout)
            advisories = data.get("advisories", {})
            for pkg_name, adv_list in advisories.items():
                if isinstance(adv_list, list):
                    for adv in adv_list:
                        if isinstance(adv, dict):
                            sev = adv.get("severity", "high")
                            findings.append({
                                "ecosystem": "php",
                                "path": str(path),
                                "package": pkg_name,
                                "severity": sev if sev in ("critical", "high", "medium", "low") else "high",
                                "cve_id": adv.get("cve") or adv.get("link", "")[:50] or "",
                            })
        except json.JSONDecodeError:
            pass

    summary = f"{len(findings)} high" if findings else "passed"
    return findings, errors, summary


def _run_cargo_audit(
    path: Path,
    fail_severity: str,
) -> tuple[list[dict], list[str], str]:
    """Run cargo audit. Returns (findings, errors, summary)."""
    findings: list[dict] = []
    errors: list[str] = []
    bin_name = "cargo"
    if shutil.which(bin_name) is None:
        errors.append(
            "cargo not found — install to enable Rust dependency audit"
        )
        return findings, errors, "cargo not installed"

    cwd = path.parent
    args = ["cargo", "audit", "--format", "json"]

    for attempt in range(3):
        try:
            proc = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                timeout=30,
                text=True,
            )
            break
        except subprocess.TimeoutExpired:
            if attempt == 2:
                errors.append("cargo audit timed out")
                return findings, errors, "timed out"
            time.sleep(2**attempt)
        except Exception as e:
            if attempt == 2:
                errors.append(f"cargo audit failed: {e}")
                return findings, errors, str(e)
            time.sleep(2**attempt)
    else:
        return findings, errors, "unknown"

    if proc.returncode != 0 and proc.stdout:
        try:
            data = json.loads(proc.stdout)
            vulns = data.get("vulnerabilities", {}).get("list", [])
            for v in vulns:
                if isinstance(v, dict):
                    sev = (v.get("advisory") or {}).get("severity", "high")
                    findings.append({
                        "ecosystem": "rust",
                        "path": str(path),
                        "package": (v.get("package") or {}).get("name", "?"),
                        "severity": sev if sev in ("critical", "high", "medium", "low") else "high",
                        "cve_id": (v.get("advisory") or {}).get("id", ""),
                    })
        except json.JSONDecodeError:
            pass

    summary = f"{len(findings)} high" if findings else "passed"
    return findings, errors, summary


def run_dependency_audit(
    workspace_path: str | Path,
    config: SecurityConfig | None,
) -> AuditResult:
    """Run dependency audit across all detected lockfiles.

    Runs audits in parallel. Fails only when severity >= fail_severity.
    """
    fail_severity = (
        config.fail_severity if config is not None else "high"
    )
    workspace = Path(workspace_path).resolve()

    lockfiles = discover_lockfiles(workspace)

    all_findings: list[dict] = []
    all_errors: list[str] = []
    summary_by_ecosystem: dict[str, str] = {}
    worst_severity: str | None = None

    severity_order = ("critical", "high", "medium", "low")

    def audit_one(item: tuple[str, Path]) -> tuple[str, list[dict], list[str], str]:
        ecosystem, path = item
        if ecosystem == "python":
            f, e, s = _run_python_audit(path, fail_severity)
        elif ecosystem == "node":
            tool_map = TOOL_BY_ECOSYSTEM["node"]
            tool = tool_map.get(path.name, "npm")
            f, e, s = _run_node_audit(path, tool, fail_severity)
        elif ecosystem == "php":
            f, e, s = _run_composer_audit(path, fail_severity)
        elif ecosystem == "rust":
            f, e, s = _run_cargo_audit(path, fail_severity)
        else:
            return ecosystem, [], [], "skipped"
        return ecosystem, f, e, s

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(audit_one, item): item for item in lockfiles}
        for fut in as_completed(futures):
            ecosystem, findings, errs, summary = fut.result()
            key = f"{ecosystem}:{futures[fut][1]}"
            summary_by_ecosystem[key] = summary
            all_errors.extend(errs)
            for f in findings:
                sev = f.get("severity", "high")
                if fail_severity in ("high", "critical") and sev in ("high", "critical"):
                    all_findings.append(f)
                elif fail_severity == "medium" and sev in ("critical", "high", "medium"):
                    all_findings.append(f)
                elif fail_severity == "low":
                    all_findings.append(f)
                if sev in severity_order and (
                    worst_severity is None
                    or severity_order.index(sev) < severity_order.index(worst_severity)
                ):
                    worst_severity = sev

    # Cap findings
    all_findings = all_findings[:100]

    # Python advisory: pyproject.toml without lockfile (we only have pyproject in lockfiles when no lockfile in that dir)
    for eco, p in lockfiles:
        if eco == "python" and p.name == "pyproject.toml":
            all_errors.append(
                "No Python lockfile detected. Recommend adding poetry.lock/uv.lock/Pipfile.lock."
            )
            break

    ok = worst_severity not in ("high", "critical")
    # CONTEXT: tool not installed = FAIL
    if ok and any("not found" in e or "not installed" in e for e in all_errors):
        ok = False

    return AuditResult(
        ok=ok,
        findings=all_findings,
        errors=all_errors,
        summary_by_ecosystem=summary_by_ecosystem,
        worst_severity=worst_severity,
    )
