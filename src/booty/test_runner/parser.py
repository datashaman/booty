"""Parse test output to extract relevant error context."""

from pathlib import Path


def extract_error_summary(stderr: str, stdout: str, max_lines: int = 100) -> str:
    """Extract concise error summary from test output.

    Prioritizes:
    1. Assertion errors with context
    2. Traceback information
    3. Test failure summaries

    Removes:
    - Verbose logging
    - Repeated stack frames
    - Test discovery output

    Args:
        stderr: Test stderr output
        stdout: Test stdout output
        max_lines: Maximum lines to include

    Returns:
        Filtered error summary suitable for LLM context
    """
    lines = []

    # Combine stderr and stdout
    combined = stderr + "\n" + stdout

    # Split into lines
    output_lines = combined.split("\n")

    # Simple heuristic: keep lines that look like errors
    in_traceback = False
    for line in output_lines:
        stripped = line.strip()

        # Start of traceback
        if stripped.startswith("Traceback (most recent call last):"):
            in_traceback = True
            lines.append(line)
            continue

        # Traceback frame
        if in_traceback and (
            stripped.startswith('File "') or stripped.startswith("  ")
        ):
            lines.append(line)
            continue

        # Error line (ends traceback)
        if in_traceback and stripped and not stripped.startswith(" "):
            lines.append(line)
            in_traceback = False
            continue

        # Assertion errors
        if "AssertionError" in line or "assert" in line.lower():
            lines.append(line)
            continue

        # Test failure summaries (pytest format)
        if stripped.startswith("FAILED ") or stripped.startswith("ERROR "):
            lines.append(line)
            continue

        # Summary lines
        if " failed" in line.lower() or " error" in line.lower():
            lines.append(line)
            continue

    # Limit to max_lines
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [
            f"\n... (truncated {len(lines) - max_lines} lines)"
        ]

    return "\n".join(lines)


def extract_files_from_output(
    output: str,
    workspace_path: Path,
) -> set[str]:
    """Extract file paths mentioned in test output.

    Parses traceback-style references and identifies workspace files.
    Excludes test files to focus on source code that needs fixing.

    Args:
        output: Combined test output (stderr + stdout)
        workspace_path: Absolute path to workspace root

    Returns:
        Set of workspace-relative paths involved in failures
    """
    involved_files = set()

    # Pattern: File "/path/to/file.py", line 123
    for line in output.split("\n"):
        stripped = line.strip()
        if stripped.startswith('File "') and '", line ' in stripped:
            # Extract path between quotes
            start = stripped.find('"') + 1
            end = stripped.find('"', start)
            file_path = Path(stripped[start:end])

            # Convert to workspace-relative if inside workspace
            try:
                relative = file_path.relative_to(workspace_path)
                relative_str = str(relative)

                # Exclude test files - we want to fix source, not tests
                if not any(part.startswith("test") for part in relative.parts):
                    involved_files.add(relative_str)
            except ValueError:
                # File outside workspace, skip
                continue

    return involved_files
