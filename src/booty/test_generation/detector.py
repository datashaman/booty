"""Convention detection for language-agnostic test generation.

This module analyzes repository structure to detect test conventions:
- Primary language (from file extensions)
- Test framework (from config files and existing tests)
- Test directory and file naming patterns (from existing tests)
"""

import configparser
import json
import tomllib
from collections import Counter
from pathlib import Path

from booty.logging import get_logger
from booty.test_generation.models import DetectedConventions

logger = get_logger()

# Language mappings by file extension
LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".rb": "ruby",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
}

# Test file patterns by language
TEST_PATTERNS = {
    "python": ["test_*.py", "*_test.py"],
    "javascript": ["*.test.js", "*.spec.js"],
    "typescript": ["*.test.ts", "*.spec.ts"],
    "go": ["*_test.go"],
    "rust": ["*_test.rs"],
    "php": ["*Test.php"],
    "ruby": ["*_test.rb", "*_spec.rb"],
    "java": ["*Test.java"],
}

# Common test directory names
TEST_DIRECTORIES = ["tests", "test", "__tests__", "spec"]

# Directories to exclude from scanning
EXCLUDED_DIRS = {".git", "node_modules", "venv", "__pycache__", "dist", "build", "target"}


def detect_conventions(workspace_path: Path) -> DetectedConventions:
    """Detect test conventions from repository structure.

    Analyzes repository to infer:
    1. Primary language (from file extensions)
    2. Test framework (from config files and test imports)
    3. Test directory and naming patterns (from existing tests)

    Args:
        workspace_path: Path to repository root

    Returns:
        DetectedConventions with inferred settings
    """
    logger.info("detecting_test_conventions", workspace=str(workspace_path))

    # Step 1: Language detection
    language = detect_primary_language(workspace_path)
    logger.debug("detected_language", language=language)

    # Step 2: Config file inspection
    config, config_path = find_and_parse_config(workspace_path, language)
    logger.debug("found_config", config_file=str(config_path) if config_path else None)

    # Step 3: Test file discovery
    test_files = find_existing_tests(workspace_path, language)
    logger.debug("found_tests", count=len(test_files))

    # Step 4: Framework detection
    framework = detect_framework(config, test_files, language)
    logger.debug("detected_framework", framework=framework)

    # Step 5: Pattern inference
    if test_files:
        test_dir = infer_test_directory(test_files)
        test_pattern = infer_naming_pattern(test_files, language)
    else:
        test_dir = None
        test_pattern = None

    logger.info(
        "convention_detection_complete",
        language=language,
        framework=framework,
        test_dir=test_dir,
        pattern=test_pattern,
    )

    return DetectedConventions(
        language=language,
        test_framework=framework,
        test_directory=test_dir,
        test_file_pattern=test_pattern,
        config_file=str(config_path) if config_path else None,
        existing_test_examples=[str(f) for f in test_files[:3]],  # Max 3 examples
    )


def detect_primary_language(workspace_path: Path) -> str:
    """Detect primary language by counting source file extensions.

    Excludes .git, node_modules, venv, __pycache__, dist, build, target.

    Args:
        workspace_path: Path to repository root

    Returns:
        Most common language, or "unknown" if no recognized files
    """
    extension_counts = Counter()

    for file_path in workspace_path.rglob("*"):
        # Skip excluded directories
        if any(part in EXCLUDED_DIRS for part in file_path.parts):
            continue

        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext in LANGUAGE_EXTENSIONS:
                extension_counts[ext] += 1

    if not extension_counts:
        logger.warning("no_recognized_files", workspace=str(workspace_path))
        return "unknown"

    # Most common extension
    most_common_ext = extension_counts.most_common(1)[0][0]
    return LANGUAGE_EXTENSIONS[most_common_ext]


def find_and_parse_config(workspace_path: Path, language: str) -> tuple[dict | None, Path | None]:
    """Find and parse language-specific config file.

    Checks:
    - Python: pyproject.toml, setup.cfg, tox.ini
    - JavaScript/TypeScript: package.json
    - Go: go.mod
    - Rust: Cargo.toml
    - PHP: composer.json

    Args:
        workspace_path: Path to repository root
        language: Detected language

    Returns:
        Tuple of (parsed_config, config_path) or (None, None) if not found
    """
    config_paths = {
        "python": ["pyproject.toml", "setup.cfg", "tox.ini"],
        "javascript": ["package.json"],
        "typescript": ["package.json"],
        "go": ["go.mod"],
        "rust": ["Cargo.toml"],
        "php": ["composer.json"],
    }

    for config_name in config_paths.get(language, []):
        config_path = workspace_path / config_name
        if config_path.exists():
            try:
                parsed = parse_config_file(config_path)
                return parsed, config_path
            except Exception as e:
                logger.warning("config_parse_error", file=config_name, error=str(e))
                continue

    return None, None


def parse_config_file(config_path: Path) -> dict:
    """Parse config file based on extension.

    Args:
        config_path: Path to config file

    Returns:
        Parsed configuration as dict
    """
    if config_path.suffix == ".toml":
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    elif config_path.suffix == ".json":
        with open(config_path) as f:
            return json.load(f)
    elif config_path.suffix in {".cfg", ".ini"}:
        parser = configparser.ConfigParser()
        parser.read(config_path)
        return {section: dict(parser[section]) for section in parser.sections()}
    else:
        return {}


def find_existing_tests(workspace_path: Path, language: str) -> list[Path]:
    """Find existing test files in the repository.

    Searches for test files matching language-specific patterns.
    Returns up to 10 test files for pattern inference.

    Args:
        workspace_path: Path to repository root
        language: Detected language

    Returns:
        List of test file paths (max 10)
    """
    test_files = []
    patterns = TEST_PATTERNS.get(language, [])

    for pattern in patterns:
        for test_file in workspace_path.rglob(pattern):
            # Skip excluded directories
            if any(part in EXCLUDED_DIRS for part in test_file.parts):
                continue

            test_files.append(test_file)
            if len(test_files) >= 10:
                break

        if len(test_files) >= 10:
            break

    return test_files


def detect_framework(config: dict | None, test_files: list[Path], language: str) -> str | None:
    """Detect test framework from config or test file imports.

    Priority:
    1. Explicit framework declaration in config
    2. Test dependencies in config
    3. Imports in existing test files

    Args:
        config: Parsed config file (or None)
        test_files: List of existing test files
        language: Detected language

    Returns:
        Framework name or None if not detected
    """
    if not config and not test_files:
        return None

    # Check config first
    if config:
        # Python: check pyproject.toml [tool.pytest.ini_options] or dependencies
        if "tool" in config and "pytest" in config["tool"]:
            return "pytest"

        # Check Python dependencies (both main and optional)
        if "project" in config:
            if "dependencies" in config["project"]:
                deps = config["project"]["dependencies"]
                if any("pytest" in dep for dep in deps):
                    return "pytest"

            if "optional-dependencies" in config["project"]:
                for group_deps in config["project"]["optional-dependencies"].values():
                    if any("pytest" in dep for dep in group_deps):
                        return "pytest"

        # JavaScript/TypeScript: check package.json devDependencies
        if "devDependencies" in config:
            if "jest" in config["devDependencies"]:
                return "jest"
            if "vitest" in config["devDependencies"]:
                return "vitest"

        # PHP: check composer.json
        if "require-dev" in config:
            if "phpunit/phpunit" in config["require-dev"]:
                return "phpunit"

    # Fallback: scan test files for imports
    if test_files:
        return detect_framework_from_imports(test_files[0], language)

    return None


def detect_framework_from_imports(test_file: Path, language: str) -> str | None:
    """Detect framework by scanning imports in a test file.

    Args:
        test_file: Path to test file
        language: Detected language

    Returns:
        Framework name or None if not detected
    """
    try:
        content = test_file.read_text()
    except Exception as e:
        logger.warning("test_file_read_error", file=str(test_file), error=str(e))
        return None

    # Python
    if language == "python":
        if "import pytest" in content or "from pytest import" in content:
            return "pytest"
        if "import unittest" in content:
            return "unittest"

    # JavaScript/TypeScript
    if language in {"javascript", "typescript"}:
        if "from 'jest'" in content or 'from "jest"' in content:
            return "jest"
        if "from 'vitest'" in content or 'from "vitest"' in content:
            return "vitest"
        if "describe(" in content and "it(" in content:
            return "jest"  # or mocha, but jest more common

    # Go
    if language == "go" and 'import "testing"' in content:
        return "go test"

    # Rust
    if language == "rust" and "#[test]" in content:
        return "cargo test"

    # PHP
    if language == "php" and "PHPUnit" in content:
        return "phpunit"

    return None


def infer_test_directory(test_files: list[Path]) -> str:
    """Infer common test directory from existing test files.

    Returns most common parent directory name that matches known test directories.

    Args:
        test_files: List of test file paths

    Returns:
        Most common test directory name, or "tests" as default
    """
    test_dirs = []
    for test_file in test_files:
        for parent in test_file.parents:
            if parent.name in TEST_DIRECTORIES:
                test_dirs.append(parent.name)
                break

    if test_dirs:
        # Most common test directory name
        return Counter(test_dirs).most_common(1)[0][0]

    return "tests"  # Default fallback


def infer_naming_pattern(test_files: list[Path], language: str) -> str:
    """Infer test file naming pattern from existing tests.

    Args:
        test_files: List of test file paths
        language: Detected language

    Returns:
        Pattern like "test_*.py" or "*.test.js"
    """
    patterns = TEST_PATTERNS.get(language, [])

    # Count matches for each pattern
    pattern_counts = {pattern: 0 for pattern in patterns}

    for test_file in test_files:
        name = test_file.name

        for pattern in patterns:
            if pattern.startswith("test_") and name.startswith("test_"):
                pattern_counts[pattern] += 1
            elif pattern.endswith("_test.py") and name.endswith("_test.py"):
                pattern_counts[pattern] += 1
            elif ".test." in pattern and ".test." in name:
                pattern_counts[pattern] += 1
            elif ".spec." in pattern and ".spec." in name:
                pattern_counts[pattern] += 1
            elif pattern.endswith("Test.php") and name.endswith("Test.php"):
                pattern_counts[pattern] += 1
            elif pattern.endswith("Test.java") and name.endswith("Test.java"):
                pattern_counts[pattern] += 1
            elif pattern.endswith("_test.go") and name.endswith("_test.go"):
                pattern_counts[pattern] += 1
            elif pattern.endswith("_test.rs") and name.endswith("_test.rs"):
                pattern_counts[pattern] += 1

    # Return most common pattern
    if any(count > 0 for count in pattern_counts.values()):
        return max(pattern_counts, key=lambda p: pattern_counts[p])

    # Default to first pattern for language
    return patterns[0] if patterns else "test_*"
