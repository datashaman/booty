"""Import and compile validation for Verifier — detect hallucinated imports and syntax errors."""

import asyncio
import json
import platform
import py_compile
import re
import sys
from pathlib import Path


def _workspace_python(workspace_path: Path) -> str:
    """Return Python executable to use for import validation.

    Prefer workspace .venv when present (has dev deps like pytest); else fall back
    to Booty's interpreter.
    """
    if platform.system() == "Windows":
        venv_py = workspace_path / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = workspace_path / ".venv" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def compile_sweep(file_paths: list[Path | str], workspace_root: Path) -> list[dict]:
    """Compile each .py file; return annotation dicts for syntax errors.

    Args:
        file_paths: Paths to Python files (may be absolute or relative to workspace)
        workspace_root: Repository root for relative path output

    Returns:
        List of annotation dicts: path, start_line, end_line, annotation_level, title, message
    """
    annotations: list[dict] = []
    for path in file_paths:
        p = Path(path) if not isinstance(path, Path) else path
        p = p if p.is_absolute() else workspace_root / p
        if not p.exists() or p.suffix != ".py":
            continue
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as e:
            se = getattr(e, "exc_value", e)
            line = getattr(se, "lineno", None) or 0
            msg = getattr(se, "msg", None) or str(e)
            try:
                rel = p.relative_to(workspace_root)
            except ValueError:
                rel = p
            path_str = str(rel).replace("\\", "/")
            annotations.append({
                "path": path_str,
                "start_line": line,
                "end_line": line,
                "annotation_level": "failure",
                "title": "Syntax error",
                "message": msg,
            })
    return annotations


async def validate_imports(
    file_paths: list[Path],
    workspace_path: Path,
    timeout: int = 60,
) -> list[dict]:
    """Validate imports resolve in workspace subprocess.

    Runs Python in workspace env; parses AST, tries importlib.import_module for each
    root module. Skipped: inside TYPE_CHECKING blocks.

    Args:
        file_paths: Paths to .py files (relative to workspace)
        workspace_path: Workspace root
        timeout: Subprocess timeout in seconds

    Returns:
        List of annotation dicts for ModuleNotFoundError
    """
    if not file_paths:
        return []

    paths_str = [str(p) for p in file_paths]
    inner = f'''import ast, importlib, json, sys
from pathlib import Path
sys.path.insert(0, {repr(str(workspace_path))})
workspace = Path({repr(str(workspace_path))})
errors = []
for arg in sys.argv[1:]:
    p = workspace / arg if not Path(arg).is_absolute() else Path(arg)
    if not p.exists():
        continue
    try:
        tree = ast.parse(p.read_text())
    except SyntaxError as e:
        errors.append({{"path": arg, "line": e.lineno or 0, "msg": str(e)}})
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                try:
                    importlib.import_module(mod)
                except ModuleNotFoundError as e:
                    errors.append({{"path": arg, "line": node.lineno, "msg": str(e)}})
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module.split(".")[0]
            try:
                importlib.import_module(mod)
            except ModuleNotFoundError as e:
                errors.append({{"path": arg, "line": node.lineno, "msg": str(e)}})
print(json.dumps(errors))
'''

    python_exe = _workspace_python(workspace_path)
    proc = await asyncio.create_subprocess_exec(
        python_exe,
        "-c",
        inner,
        "--",
        *paths_str,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(workspace_path),
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        return [{
            "path": paths_str[0] if paths_str else "",
            "start_line": 1,
            "end_line": 1,
            "annotation_level": "failure",
            "title": "Import validation timeout",
            "message": f"Subprocess exceeded {timeout}s",
        }]

    raw = stdout.decode("utf-8", errors="replace").strip()
    if not raw:
        return []
    try:
        errors = json.loads(raw)
    except json.JSONDecodeError:
        return [{
            "path": paths_str[0] if paths_str else "",
            "start_line": 1,
            "end_line": 1,
            "annotation_level": "failure",
            "title": "Import validation error",
            "message": raw[:200],
        }]

    return [
        {
            "path": e.get("path", ""),
            "start_line": e.get("line", 0),
            "end_line": e.get("line", 0),
            "annotation_level": "failure",
            "title": "Unresolved import",
            "message": e.get("msg", ""),
        }
        for e in errors
    ]


def parse_setup_stderr(stderr: str, workspace_path: Path) -> list[dict]:
    """Parse setup_command stderr for file:line patterns.

    Matches: File "path", line N and path:N:

    Args:
        stderr: stderr from setup command
        workspace_path: For relativizing paths

    Returns:
        List of annotation dicts
    """
    annotations: list[dict] = []
    # File "path", line N
    pattern1 = re.compile(
        r'File\s+"([^"]+)"\s*,\s*line\s+(\d+)',
        re.MULTILINE,
    )
    # path:N: or path:line N
    pattern2 = re.compile(r"([^\s:]+):(\d+):?")
    seen: set[tuple[str, int, str]] = set()

    for m in pattern1.finditer(stderr):
        path, line_s = m.group(1), m.group(2)
        line = int(line_s)
        try:
            rel = Path(path).relative_to(workspace_path)
        except ValueError:
            rel = Path(path)
        path_str = str(rel).replace("\\", "/")
        key = (path_str, line, "setup")
        if key in seen:
            continue
        seen.add(key)
        context = stderr[max(0, m.start() - 50) : m.end() + 80]
        annotations.append({
            "path": path_str,
            "start_line": line,
            "end_line": line,
            "annotation_level": "failure",
            "title": "Setup command error",
            "message": context.strip()[:500],
        })

    for m in pattern2.finditer(stderr):
        path, line_s = m.group(1), m.group(2)
        line = int(line_s)
        try:
            rel = Path(path).relative_to(workspace_path)
        except ValueError:
            rel = Path(path)
        path_str = str(rel).replace("\\", "/")
        key = (path_str, line, "setup2")
        if key in seen:
            continue
        seen.add(key)
        annotations.append({
            "path": path_str,
            "start_line": line,
            "end_line": line,
            "annotation_level": "failure",
            "title": "Setup command error",
            "message": stderr[m.start() : m.end() + 100][:500],
        })

    return annotations


def prepare_check_annotations(
    annotations: list[dict],
    cap: int = 50,
) -> tuple[list[dict], bool]:
    """Deduplicate and cap annotations for GitHub Checks API.

    Args:
        annotations: Raw annotation dicts
        cap: Max annotations to return (API limit 50)

    Returns:
        (annotations, truncated) — truncated True if original exceeded cap
    """
    seen: set[tuple[str, int, str]] = set()
    deduped: list[dict] = []
    for a in annotations:
        path = a.get("path", "")
        line = a.get("start_line", 0)
        msg = a.get("message", "")
        key = (path, line, msg)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(a)

    truncated = len(deduped) > cap
    return (deduped[:cap], truncated)
