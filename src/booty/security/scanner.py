"""Secret scanning via gitleaks or trufflehog."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from booty.test_runner.config import SecurityConfig


@dataclass
class ScanResult:
    """Result of a secret scan."""

    findings: list[dict]
    scan_ok: bool
    error_message: str | None = None


def run_secret_scan(
    workspace_path: str,
    base_sha: str,
    head_sha: str,
    config: SecurityConfig | None,
) -> ScanResult:
    """Run secret scan on git diff base..head.

    Uses gitleaks preferred; trufflehog fallback if gitleaks missing.
    Returns ScanResult with findings or error.
    """
    scanner_bin = "gitleaks"
    if config is not None:
        scanner_bin = config.secret_scanner

    # Resolve binary: try chosen first, then fallback
    if scanner_bin == "gitleaks":
        which = shutil.which("gitleaks") or shutil.which("trufflehog")
        if which is None:
            return ScanResult(
                findings=[],
                scan_ok=False,
                error_message="Secret scanner not found (gitleaks or trufflehog)",
            )
        scanner_bin = Path(which).name
    else:  # trufflehog
        which = shutil.which("trufflehog") or shutil.which("gitleaks")
        if which is None:
            return ScanResult(
                findings=[],
                scan_ok=False,
                error_message="Secret scanner not found (trufflehog or gitleaks)",
            )
        scanner_bin = Path(which).name

    workspace = Path(workspace_path)
    if not workspace.exists():
        return ScanResult(
            findings=[],
            scan_ok=False,
            error_message=f"Workspace not found: {workspace_path}",
        )

    try:
        # git diff base..head
        diff_proc = subprocess.Popen(
            ["git", "diff", f"{base_sha}..{head_sha}", "--", "."],
            cwd=workspace_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
        diff_out, diff_err = diff_proc.communicate(timeout=30)
        if diff_proc.returncode != 0 and diff_proc.returncode is not None:
            return ScanResult(
                findings=[],
                scan_ok=False,
                error_message=f"git diff failed: {diff_err.decode(errors='replace')}",
            )

        # Empty diff: no changed content
        if not diff_out.strip():
            return ScanResult(findings=[], scan_ok=True)

        # Run gitleaks stdin (trufflehog not implemented for stdin flow)
        if scanner_bin == "trufflehog":
            return ScanResult(
                findings=[],
                scan_ok=False,
                error_message="trufflehog diff scan not implemented; use gitleaks",
            )

        # gitleaks stdin --report-format=json --report-path=-
        gitleaks_proc = subprocess.run(
            [
                "gitleaks",
                "stdin",
                "--no-banner",
                "--report-format=json",
                "--report-path=-",
            ],
            input=diff_out,
            capture_output=True,
            timeout=55,
            cwd=workspace_path,
        )

        # Exit 0 = no findings, 1 = findings, 2 = error
        if gitleaks_proc.returncode == 2:
            err = gitleaks_proc.stderr.decode(errors="replace").strip()
            return ScanResult(
                findings=[],
                scan_ok=False,
                error_message=f"gitleaks failed: {err or 'unknown error'}",
            )

        findings: list[dict] = []
        if gitleaks_proc.stdout:
            try:
                raw = json.loads(gitleaks_proc.stdout.decode("utf-8"))
                # gitleaks json: can be {"findings": [...]} or list
                if isinstance(raw, dict) and "findings" in raw:
                    items = raw["findings"]
                elif isinstance(raw, list):
                    items = raw
                else:
                    items = []

                for f in items:
                    if isinstance(f, dict):
                        path = f.get("File") or f.get("file") or f.get("path") or ""
                        start = f.get("StartLine") or f.get("Line") or f.get("line") or 1
                        end = f.get("EndLine") or f.get("end_line") or start
                        rule_id = f.get("RuleID") or f.get("rule_id") or "unknown"
                        secret = f.get("Secret") or f.get("secret") or ""
                        findings.append(
                            {
                                "path": str(path),
                                "start_line": int(start) if start else 1,
                                "end_line": int(end) if end else 1,
                                "rule_id": str(rule_id),
                                "secret": secret[:20] + "..." if len(secret) > 20 else secret,
                            }
                        )
            except json.JSONDecodeError:
                pass

        return ScanResult(findings=findings, scan_ok=True)

    except subprocess.TimeoutExpired:
        return ScanResult(
            findings=[],
            scan_ok=False,
            error_message="Scan timed out",
        )
    except Exception as e:
        return ScanResult(
            findings=[],
            scan_ok=False,
            error_message=str(e),
        )


def build_annotations(
    findings: list[dict],
    max_count: int = 50,
) -> tuple[list[dict], str]:
    """Convert findings to GitHub annotation format, cap at max_count.

    Returns (annotations, summary_suffix). Suffix is " and N more" when truncated.
    """
    if not findings:
        return [], ""

    # Sort by (path, start_line)
    sorted_findings = sorted(
        findings,
        key=lambda f: (f.get("path", ""), f.get("start_line", 0)),
    )

    annotations: list[dict] = []
    for f in sorted_findings[:max_count]:
        path = f.get("path", "")
        start_line = f.get("start_line", 1)
        end_line = f.get("end_line", start_line)
        rule_id = f.get("rule_id", "secret")

        annotations.append(
            {
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
                "annotation_level": "failure",
                "message": f"Secret detected: {rule_id}",
                "title": "Secret detected",
            }
        )

    remainder = len(findings) - max_count
    suffix = f" and {remainder} more" if remainder > 0 else ""
    return annotations, suffix
