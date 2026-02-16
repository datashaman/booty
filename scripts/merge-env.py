#!/usr/bin/env python3
"""Merge new/updated vars from .env.example into .env.

Preserves your existing values. Adds any vars from .env.example that are
missing in .env (using the example's format). Run from project root.
"""

from pathlib import Path
import re
import sys


def parse_env(path: Path) -> dict[str, str]:
    """Parse .env file into key=value dict. Ignores comments."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            result[key.strip()] = val.strip()
    return result


def parse_example(path: Path) -> list[tuple[str | None, str]]:
    """Parse .env.example into list of (comment_block_or_none, line).
    Comments and blanks accumulate; a line with '=' is a var (possibly #-prefixed).
    """
    raw_lines = path.read_text().splitlines()
    result: list[tuple[str | None, str]] = []
    block: list[str] = []
    for raw in raw_lines:
        line = raw.rstrip()
        has_var = "=" in line
        if not has_var:
            block.append(line)
            continue
        comment = "\n".join(block) if block else None
        block = []
        result.append((comment, line))
    if block:
        result.append(("\n".join(block), ""))
    return result


def extract_key(line: str) -> str | None:
    """Extract KEY from 'KEY=val' or '# KEY=val'."""
    s = line.strip()
    if s.startswith("#"):
        s = s[1:].strip()
    if "=" in s:
        return s.partition("=")[0].strip()
    return None


def merge(example_path: Path, env_path: Path, out_path: Path | None = None) -> str:
    """Merge example into env. Returns merged content."""
    out_path = out_path or env_path
    env_vars = parse_env(env_path)
    entries = parse_example(example_path)
    lines: list[str] = []
    seen_keys: set[str] = set()

    for comment, line in entries:
        if comment:
            lines.append(comment)
        if not line:
            if comment and comment.endswith("\n"):
                pass
            elif lines and not lines[-1].strip() == "":
                lines.append("")
            continue

        key = extract_key(line)
        if key:
            seen_keys.add(key)
            if key in env_vars:
                lines.append(f"{key}={env_vars[key]}")
            else:
                lines.append(line)
        else:
            lines.append(line)

    # Append any .env vars not in example
    extra = {k: v for k, v in env_vars.items() if k not in seen_keys}
    if extra:
        lines.append("")
        lines.append("# User-defined (not in .env.example)")
        for k, v in sorted(extra.items()):
            lines.append(f"{k}={v}")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Merge .env.example into .env")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Show merged output, don't write")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    example = root / ".env.example"
    env = root / ".env"

    if not example.exists():
        print("error: .env.example not found", file=sys.stderr)
        sys.exit(1)

    content = merge(example, env)
    if args.dry_run:
        print(content)
    else:
        env.write_text(content)
        print("merged .env.example → .env")


if __name__ == "__main__":
    main()
