"""Import validation for generated test files.

This module validates that generated test imports don't hallucinate non-existent packages.
Uses AST parsing for Python to extract and validate imports against:
- Standard library modules
- Project's own modules
- Declared dependencies in pyproject.toml or requirements.txt
"""

import ast
import re
import sys
from pathlib import Path

from booty.logging import get_logger

logger = get_logger()

# Common package name aliases where PyPI name differs from import name
# e.g., "Pillow" (PyPI) -> "PIL" (import)
COMMON_ALIASES = {
    "pillow": "PIL",
    "python-dateutil": "dateutil",
    "beautifulsoup4": "bs4",
    "scikit-learn": "sklearn",
    "opencv-python": "cv2",
    "pyyaml": "yaml",
    "python-magic": "magic",
}


def validate_test_imports(
    test_file_content: str,
    language: str,
    workspace_path: Path,
) -> tuple[bool, list[str]]:
    """Validate that test imports don't hallucinate non-existent packages.

    Checks test imports against:
    - Standard library (for Python)
    - Project's own modules (from src/, root)
    - Declared dependencies (from pyproject.toml, requirements.txt, etc.)

    Args:
        test_file_content: Content of generated test file
        language: Programming language ("python", "javascript", etc.)
        workspace_path: Path to repository root

    Returns:
        Tuple of (is_valid, error_messages)
        - (True, []) if all imports are valid
        - (False, [errors]) if invalid imports found
    """
    if language == "python":
        errors = validate_python_imports(test_file_content, workspace_path)
        return (len(errors) == 0, errors)
    else:
        # Non-Python languages: validation deferred per RESEARCH.md open question #5
        logger.debug("import_validation_skipped", language=language)
        return (True, [])


def validate_python_imports(test_content: str, workspace_path: Path) -> list[str]:
    """Validate Python imports against project structure and installed packages.

    Checks:
    1. Standard library imports (always valid)
    2. Project-internal imports (from src/ or root)
    3. Declared dependencies (from pyproject.toml, requirements.txt)

    Args:
        test_content: Python test file content
        workspace_path: Path to repository root

    Returns:
        List of error messages (empty if all imports valid)
    """
    errors = []

    # Parse AST
    try:
        tree = ast.parse(test_content)
    except SyntaxError as e:
        return [f"Syntax error in test file: {e}"]

    # Extract imports
    imports = extract_imports(tree)
    logger.debug("extracted_imports", imports=imports)

    # Get validation sources
    stdlib_modules = get_stdlib_modules()
    project_modules = get_project_modules(workspace_path)
    dependencies = get_project_dependencies(workspace_path)

    logger.debug(
        "validation_sources",
        stdlib_count=len(stdlib_modules),
        project_count=len(project_modules),
        deps_count=len(dependencies),
    )

    # Check each import
    for imp in imports:
        if imp in stdlib_modules:
            continue  # Stdlib is always available
        if imp in project_modules:
            continue  # Project's own modules
        if imp in dependencies:
            continue  # Declared dependency

        # Check aliases (e.g., PIL -> Pillow)
        if any(normalize_name(imp) == normalize_name(alias) for alias in COMMON_ALIASES.values()):
            continue  # Known alias import

        # Import not found - potential hallucination
        errors.append(
            f"Import '{imp}' not found in stdlib, project modules, or dependencies. "
            f"This may be a hallucinated package."
        )
        logger.warning("potential_hallucination", import_name=imp)

    return errors


def extract_imports(tree: ast.AST) -> list[str]:
    """Extract all import module names from AST.

    Extracts root module names from both:
    - import foo.bar.baz -> "foo"
    - from foo.bar import baz -> "foo"

    Args:
        tree: Parsed AST

    Returns:
        List of root module names
    """
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Get root module name (e.g., "os.path" -> "os")
                root_module = alias.name.split(".")[0]
                imports.append(root_module)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                # Get root module name
                root_module = node.module.split(".")[0]
                imports.append(root_module)

    return list(set(imports))  # Deduplicate


def get_stdlib_modules() -> set[str]:
    """Get set of Python stdlib module names.

    Uses sys.stdlib_module_names (Python 3.10+).

    Returns:
        Set of stdlib module names
    """
    return set(sys.stdlib_module_names)


def get_project_modules(workspace_path: Path) -> set[str]:
    """Get set of project's own module names from src/ and root directories.

    Scans for:
    - Directories with __init__.py (packages)
    - Standalone .py files (modules)

    Args:
        workspace_path: Path to repository root

    Returns:
        Set of project module names
    """
    modules = set()

    # Check common source directories
    for src_dir in ["src", "."]:
        src_path = workspace_path / src_dir
        if not src_path.exists():
            continue

        for item in src_path.iterdir():
            # Skip hidden files and common non-module directories
            if item.name.startswith(".") or item.name in {"tests", "test", "docs", "dist", "build"}:
                continue

            if item.is_dir() and (item / "__init__.py").exists():
                modules.add(item.name)
            elif item.suffix == ".py":
                modules.add(item.stem)

    return modules


def get_project_dependencies(workspace_path: Path) -> set[str]:
    """Extract declared dependencies from pyproject.toml or requirements.txt.

    Parses:
    - pyproject.toml: [project.dependencies] and [project.optional-dependencies]
    - requirements.txt: all packages listed

    Args:
        workspace_path: Path to repository root

    Returns:
        Set of package names (normalized)
    """
    deps = set()

    # Try pyproject.toml
    pyproject = workspace_path / "pyproject.toml"
    if pyproject.exists():
        deps.update(parse_pyproject_deps(pyproject))

    # Try requirements.txt
    requirements = workspace_path / "requirements.txt"
    if requirements.exists():
        deps.update(parse_requirements_txt(requirements))

    # Normalize all dependency names and add known aliases
    normalized_deps = set()
    for dep in deps:
        normalized = normalize_name(dep)
        normalized_deps.add(normalized)
        # Add known import alias if exists
        if normalized in COMMON_ALIASES:
            normalized_deps.add(COMMON_ALIASES[normalized].lower())

    return normalized_deps


def parse_pyproject_deps(pyproject_path: Path) -> set[str]:
    """Parse dependencies from pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml

    Returns:
        Set of package names
    """
    import tomllib

    deps = set()

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        # Extract from [project.dependencies]
        if "project" in data and "dependencies" in data["project"]:
            for dep in data["project"]["dependencies"]:
                pkg_name = extract_package_name(dep)
                if pkg_name:
                    deps.add(pkg_name)

        # Extract from [project.optional-dependencies]
        if "project" in data and "optional-dependencies" in data["project"]:
            for group in data["project"]["optional-dependencies"].values():
                for dep in group:
                    pkg_name = extract_package_name(dep)
                    if pkg_name:
                        deps.add(pkg_name)

    except Exception as e:
        logger.warning("pyproject_parse_error", error=str(e))

    return deps


def parse_requirements_txt(requirements_path: Path) -> set[str]:
    """Parse dependencies from requirements.txt.

    Args:
        requirements_path: Path to requirements.txt

    Returns:
        Set of package names
    """
    deps = set()

    try:
        for line in requirements_path.read_text().splitlines():
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            pkg_name = extract_package_name(line)
            if pkg_name:
                deps.add(pkg_name)
    except Exception as e:
        logger.warning("requirements_parse_error", error=str(e))

    return deps


def extract_package_name(dep_line: str) -> str | None:
    """Extract package name from dependency line.

    Handles formats like:
    - "package>=1.0.0"
    - "package[extra]>=1.0.0"
    - "package"

    Args:
        dep_line: Dependency specification string

    Returns:
        Package name or None if invalid
    """
    # Split on version specifiers: >=, <=, ==, !=, <, >, ~=, [
    parts = re.split(r"[><=!~;\[]", dep_line)
    if parts:
        pkg_name = parts[0].strip()
        return pkg_name if pkg_name else None
    return None


def normalize_name(name: str) -> str:
    """Normalize package/module name for comparison.

    Converts to lowercase and removes hyphens/underscores.

    Args:
        name: Package or module name

    Returns:
        Normalized name
    """
    return name.lower().replace("-", "").replace("_", "")
