# Phase 5: Test Generation - Research

**Researched:** 2026-02-15
**Domain:** LLM-based test generation with language-agnostic convention detection
**Confidence:** HIGH

## Summary

This phase extends Booty's existing code generation to produce tests alongside source code. The core challenge is language-agnostic test convention detection—inferring test framework, directory structure, naming patterns, and configuration from target repositories without hardcoded defaults.

Research reveals a **combo detection approach** is optimal: structured code performs initial detection (file scanning, config parsing, language identification), then LLM receives these findings as context for informed test generation. This leverages LLMs' strength (understanding intent, generating code) while avoiding their weakness (hallucinating non-existent imports/packages).

**Key architectural decision from CONTEXT.md:** Single LLM call generates both code and tests (shared context), with one-shot test generation (tests aren't refined, only source code is). This preserves the existing refinement loop's stability while ensuring tests reflect the LLM's understanding of correct behavior.

**Primary recommendation:** Build convention detection as a separate, cacheable detection phase that runs once per repository, then inject detected conventions into the existing code generation prompt. Validate generated test imports against actual project dependencies before execution.

## Standard Stack

The established libraries/tools for this domain:

### Core (Python-specific - Booty's implementation language)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tomllib | stdlib (3.11+) | Parse pyproject.toml | Built-in TOML parser, zero dependencies |
| pathlib | stdlib | File operations | Standard file handling, cross-platform |
| json | stdlib | Parse package.json, go.mod | Built-in JSON parser |

### Supporting (Language Detection)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| File extension mapping | N/A | Primary language detection | Always - fastest, most reliable |
| Config file inspection | N/A | Framework detection | After language identified |
| Existing test scanning | N/A | Convention inference | When tests exist in repo |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| File extensions | Guesslang (ML-based) | Adds TensorFlow dependency (172MB+), 93% accuracy vs 99%+ for extensions |
| File extensions | tree-sitter | Complex setup, overkill for file-level detection |
| Custom TOML parser | toml (deprecated) | tomllib is stdlib in Python 3.11+ |
| Pattern matching | Linguist | Ruby dependency, GitHub-specific |

**Installation:**
```bash
# No additional dependencies needed - all stdlib
# Project already has PyYAML for .booty.yml parsing
```

## Architecture Patterns

### Recommended Project Structure
```
src/booty/
├── test_generation/          # New module
│   ├── __init__.py
│   ├── detector.py            # Convention detection
│   ├── models.py              # DetectedConventions Pydantic model
│   └── validator.py           # Import validation
├── llm/
│   ├── prompts.py             # EXTEND: add test context to existing prompts
│   └── models.py              # EXTEND: add test_files to CodeGenerationPlan
└── code_gen/
    └── generator.py           # EXTEND: validate tests, apply conventions
```

### Pattern 1: Convention Detection (Structural Analysis)
**What:** Analyze repository structure once to infer test conventions
**When to use:** Before first test generation, cache results per repository

**Detection priority order:**
1. **Language identification** (file extensions in workspace)
2. **Config file inspection** (pyproject.toml, package.json, go.mod, Cargo.toml, etc.)
3. **Existing test discovery** (scan for test files, infer patterns)
4. **Framework detection** (from config + test imports)

**Example:**
```python
# Source: Pattern from research synthesis
from pathlib import Path
from dataclasses import dataclass

@dataclass
class DetectedConventions:
    """Detected test conventions for a repository."""
    language: str                    # "python", "go", "javascript", etc.
    test_framework: str | None       # "pytest", "jest", "go test", etc.
    test_directory: str              # "tests/", "__tests__/", "test/", etc.
    test_file_pattern: str           # "test_*.py", "*.test.js", "*_test.go"
    config_file: Path | None         # pyproject.toml, package.json, etc.
    existing_test_examples: list[Path]  # Sample test files for reference

def detect_conventions(workspace_path: Path) -> DetectedConventions:
    """Detect test conventions from repository structure.

    1. Identify primary language from file extensions
    2. Locate and parse relevant config files
    3. Scan for existing test files and infer patterns
    4. Extract framework from config or test imports
    """
    # Step 1: Language detection
    language = detect_primary_language(workspace_path)

    # Step 2: Config file inspection
    config = find_and_parse_config(workspace_path, language)

    # Step 3: Test file discovery
    test_files = find_existing_tests(workspace_path, language)

    # Step 4: Framework detection
    framework = detect_framework(config, test_files)

    # Step 5: Pattern inference
    if test_files:
        test_dir = infer_test_directory(test_files)
        test_pattern = infer_naming_pattern(test_files, language)
    else:
        # No existing tests - cannot infer, LLM must decide
        test_dir = None
        test_pattern = None

    return DetectedConventions(
        language=language,
        test_framework=framework,
        test_directory=test_dir,
        test_file_pattern=test_pattern,
        config_file=config,
        existing_test_examples=test_files[:3],  # Max 3 examples
    )
```

### Pattern 2: Language Detection (File Extension Counting)
**What:** Identify primary language by counting file extensions
**When to use:** First step of convention detection

**Example:**
```python
# Source: Pattern from research + Python stdlib
from collections import Counter
from pathlib import Path

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

def detect_primary_language(workspace_path: Path) -> str:
    """Detect primary language by counting source file extensions.

    Returns most common language, or "unknown" if no recognized files.
    Excludes: .git, node_modules, venv, __pycache__, dist, build
    """
    extension_counts = Counter()

    for file_path in workspace_path.rglob("*"):
        # Skip excluded directories
        if any(part in {".git", "node_modules", "venv", "__pycache__",
                        "dist", "build", "target"}
               for part in file_path.parts):
            continue

        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext in LANGUAGE_EXTENSIONS:
                extension_counts[ext] += 1

    if not extension_counts:
        return "unknown"

    # Most common extension
    most_common_ext = extension_counts.most_common(1)[0][0]
    return LANGUAGE_EXTENSIONS[most_common_ext]
```

### Pattern 3: Config File Inspection
**What:** Parse language-specific config files to detect test framework
**When to use:** After language detection

**Example:**
```python
# Source: Python packaging docs, research synthesis
import json
import tomllib
from pathlib import Path

def find_and_parse_config(workspace_path: Path, language: str) -> dict | None:
    """Find and parse language-specific config file.

    Python: pyproject.toml, setup.cfg, tox.ini
    JavaScript: package.json
    Go: go.mod
    Rust: Cargo.toml
    PHP: composer.json
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
            return parse_config_file(config_path)

    return None

def parse_config_file(config_path: Path) -> dict:
    """Parse config file based on extension."""
    if config_path.suffix == ".toml":
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    elif config_path.suffix == ".json":
        with open(config_path, "r") as f:
            return json.load(f)
    elif config_path.suffix in {".cfg", ".ini"}:
        # Basic INI parsing for setup.cfg, tox.ini
        import configparser
        parser = configparser.ConfigParser()
        parser.read(config_path)
        return {section: dict(parser[section]) for section in parser.sections()}
    else:
        return {}

def detect_framework(config: dict | None, test_files: list[Path]) -> str | None:
    """Detect test framework from config or test file imports.

    Priority:
    1. Explicit framework declaration in config
    2. Test dependencies in config
    3. Imports in existing test files
    """
    if not config and not test_files:
        return None

    # Python: check pyproject.toml [tool.pytest.ini_options] or dependencies
    if config:
        # pytest detection
        if "tool" in config and "pytest" in config["tool"]:
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
        return detect_framework_from_imports(test_files[0])

    return None

def detect_framework_from_imports(test_file: Path) -> str | None:
    """Detect framework by scanning imports in a test file."""
    content = test_file.read_text()

    # Python
    if "import pytest" in content or "from pytest import" in content:
        return "pytest"
    if "import unittest" in content:
        return "unittest"

    # JavaScript/TypeScript
    if "from 'jest'" in content or 'from "jest"' in content:
        return "jest"
    if "describe(" in content and "it(" in content:
        return "jest"  # or mocha, but jest more common

    # Go
    if test_file.suffix == ".go" and "testing" in content:
        return "go test"

    # Rust
    if test_file.suffix == ".rs" and "#[test]" in content:
        return "cargo test"

    # PHP
    if "PHPUnit" in content:
        return "phpunit"

    return None
```

### Pattern 4: Test File Discovery and Pattern Inference
**What:** Find existing test files and infer naming/directory conventions
**When to use:** After language detection

**Example:**
```python
# Source: pytest docs, Jest docs, Go/Rust conventions from research
from pathlib import Path

# Test file patterns by language
TEST_PATTERNS = {
    "python": ["test_*.py", "*_test.py"],
    "javascript": ["*.test.js", "*.spec.js"],
    "typescript": ["*.test.ts", "*.spec.ts"],
    "go": ["*_test.go"],
    "rust": ["*_test.rs"],
    "php": ["*Test.php"],
}

# Common test directory names
TEST_DIRECTORIES = ["tests", "test", "__tests__", "spec"]

def find_existing_tests(workspace_path: Path, language: str) -> list[Path]:
    """Find existing test files in the repository.

    Searches for test files matching language-specific patterns.
    Returns up to 10 test files (for pattern inference).
    """
    test_files = []
    patterns = TEST_PATTERNS.get(language, [])

    for pattern in patterns:
        for test_file in workspace_path.rglob(pattern):
            # Skip excluded directories
            if any(part in {".git", "node_modules", "venv", "__pycache__"}
                   for part in test_file.parts):
                continue

            test_files.append(test_file)
            if len(test_files) >= 10:
                break

        if len(test_files) >= 10:
            break

    return test_files

def infer_test_directory(test_files: list[Path]) -> str:
    """Infer common test directory from existing test files.

    Returns most common parent directory name that looks like a test dir.
    """
    test_dirs = []
    for test_file in test_files:
        for parent in test_file.parents:
            if parent.name in TEST_DIRECTORIES:
                test_dirs.append(parent.name)
                break

    if test_dirs:
        # Most common test directory name
        from collections import Counter
        return Counter(test_dirs).most_common(1)[0][0]

    return "tests"  # Default fallback

def infer_naming_pattern(test_files: list[Path], language: str) -> str:
    """Infer test file naming pattern from existing tests.

    Returns pattern like "test_*.py" or "*.test.js".
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

    # Return most common pattern
    if any(count > 0 for count in pattern_counts.values()):
        return max(pattern_counts, key=pattern_counts.get)

    # Default to first pattern for language
    return patterns[0] if patterns else "test_*.{ext}"
```

### Pattern 5: LLM Prompt Injection with Detected Conventions
**What:** Inject detected conventions into code generation prompt
**When to use:** During code generation, after convention detection

**Example:**
```python
# Source: Research on context injection for test generation
from booty.test_generation.models import DetectedConventions

def format_test_conventions_for_prompt(conventions: DetectedConventions) -> str:
    """Format detected conventions as context for LLM prompt.

    This is injected into the existing code generation prompt to guide
    test generation according to repository conventions.
    """
    parts = [
        "## Test Generation Requirements",
        "",
        "Generate unit tests alongside code changes following these repository conventions:",
        "",
        f"**Language:** {conventions.language}",
    ]

    if conventions.test_framework:
        parts.append(f"**Test Framework:** {conventions.test_framework}")
    else:
        parts.append("**Test Framework:** Unknown - LLM should infer appropriate framework")

    if conventions.test_directory:
        parts.append(f"**Test Directory:** {conventions.test_directory}/")
    else:
        parts.append("**Test Directory:** No existing tests - LLM should choose conventional location")

    if conventions.test_file_pattern:
        parts.append(f"**Test File Naming:** {conventions.test_file_pattern}")
    else:
        parts.append("**Test File Naming:** No existing tests - LLM should follow language conventions")

    parts.extend([
        "",
        "**CRITICAL:** Use ONLY imports that exist in the project dependencies.",
        "DO NOT hallucinate package names or import paths.",
        "Verify all test imports match the detected framework and project structure.",
    ])

    if conventions.existing_test_examples:
        parts.extend([
            "",
            "**Example Test Files (for reference):**",
        ])
        for example in conventions.existing_test_examples[:2]:
            parts.append(f"- {example}")

    return "\n".join(parts)

# Extend existing prompt in llm/prompts.py
def _generate_code_changes_impl_with_tests(
    analysis_summary: str,
    file_contents_formatted: str,
    test_conventions: str,  # NEW: injected conventions
    issue_title: str,
    issue_body: str,
) -> CodeGenerationPlan:
    """Extended version of code generation that includes test generation.

    Prompt modification:
    - Add test_conventions section after file_contents_formatted
    - Extend requirements to include test generation
    - Update CodeGenerationPlan to include test_files
    """
    ...
```

### Pattern 6: Import Validation (Anti-Hallucination)
**What:** Validate generated test imports before execution
**When to use:** After LLM generates tests, before applying to workspace

**Example:**
```python
# Source: Research on package hallucination prevention
from pathlib import Path
import re
import ast

def validate_test_imports(
    test_file_content: str,
    language: str,
    workspace_path: Path,
) -> tuple[bool, list[str]]:
    """Validate that test imports don't hallucinate non-existent packages.

    Returns:
        (is_valid, error_messages)
    """
    errors = []

    if language == "python":
        errors.extend(validate_python_imports(test_file_content, workspace_path))
    elif language in {"javascript", "typescript"}:
        errors.extend(validate_js_imports(test_file_content, workspace_path))
    # Add other languages as needed

    return (len(errors) == 0, errors)

def validate_python_imports(test_content: str, workspace_path: Path) -> list[str]:
    """Validate Python imports against project structure and installed packages.

    Checks:
    1. Relative imports match project structure
    2. Third-party imports exist in dependencies
    3. Standard library imports are valid
    """
    errors = []

    try:
        tree = ast.parse(test_content)
    except SyntaxError as e:
        return [f"Syntax error in test file: {e}"]

    # Extract imports
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])

    # Check each import
    stdlib_modules = get_stdlib_modules()  # List of stdlib modules
    project_modules = get_project_modules(workspace_path)  # From src/

    # Load dependencies from pyproject.toml or requirements.txt
    dependencies = get_project_dependencies(workspace_path)

    for imp in imports:
        if imp in stdlib_modules:
            continue  # Stdlib is always available
        if imp in project_modules:
            continue  # Project's own modules
        if imp in dependencies:
            continue  # Declared dependency

        # Import not found - potential hallucination
        errors.append(
            f"Import '{imp}' not found in stdlib, project modules, or dependencies. "
            f"This may be a hallucinated package."
        )

    return errors

def get_project_dependencies(workspace_path: Path) -> set[str]:
    """Extract declared dependencies from pyproject.toml or requirements.txt."""
    deps = set()

    # Try pyproject.toml
    pyproject = workspace_path / "pyproject.toml"
    if pyproject.exists():
        import tomllib
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)

        # Extract from [project.dependencies]
        if "project" in data and "dependencies" in data["project"]:
            for dep in data["project"]["dependencies"]:
                # Parse "package>=1.0.0" -> "package"
                pkg_name = re.split(r"[><=!]", dep)[0].strip()
                deps.add(pkg_name)

        # Extract from [project.optional-dependencies]
        if "project" in data and "optional-dependencies" in data["project"]:
            for group in data["project"]["optional-dependencies"].values():
                for dep in group:
                    pkg_name = re.split(r"[><=!]", dep)[0].strip()
                    deps.add(pkg_name)

    # Try requirements.txt
    requirements = workspace_path / "requirements.txt"
    if requirements.exists():
        for line in requirements.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                pkg_name = re.split(r"[><=!]", line)[0].strip()
                deps.add(pkg_name)

    return deps

def get_stdlib_modules() -> set[str]:
    """Get set of Python stdlib module names."""
    import sys
    return set(sys.stdlib_module_names)  # Python 3.10+

def get_project_modules(workspace_path: Path) -> set[str]:
    """Get set of project's own module names from src/ directory."""
    modules = set()

    # Check common source directories
    for src_dir in ["src", "."]:
        src_path = workspace_path / src_dir
        if not src_path.exists():
            continue

        for item in src_path.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                modules.add(item.name)
            elif item.suffix == ".py":
                modules.add(item.stem)

    return modules
```

### Anti-Patterns to Avoid

- **Hardcoded defaults by language:** "Python repos always use pytest" - some use unittest, nose2, etc. Always detect.
- **Ignoring existing tests:** Existing tests are the ground truth for conventions - always scan and infer.
- **Running detection on every PR:** Convention detection is expensive - cache results per repository.
- **Generating tests without validation:** LLMs hallucinate imports 19.7% of the time - always validate before execution.
- **Separate test-only LLM call:** Context lost, duplicates work - generate tests alongside code in one call.
- **Refining tests in loop:** Tests represent expected behavior - only refine source code to match tests.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TOML parsing | Custom parser | tomllib (stdlib 3.11+) | TOML spec has edge cases, stdlib is battle-tested |
| Language detection | AST parsing, ML models | File extension counting | Extensions are 99%+ accurate, simpler, faster |
| Import extraction | Regex parsing | ast.parse() (Python), tree-sitter (others) | Regex breaks on edge cases, AST is correct |
| Dependency resolution | Manual file parsing | Built-in package tools (pip, npm, cargo) | Handles version constraints, platform-specific deps |
| Test framework detection | Heuristics only | Config file inspection THEN heuristics | Config is authoritative, heuristics are fallback |

**Key insight:** Convention detection is pattern recognition over structured data. Use standard parsers (tomllib, json, ast) rather than custom string manipulation - they handle edge cases correctly.

## Common Pitfalls

### Pitfall 1: Package Hallucination (HIGH SEVERITY)
**What goes wrong:** LLM generates test imports for non-existent packages (19.7% hallucination rate in research)
**Why it happens:** LLMs are trained on code but don't know which packages exist in the current project
**How to avoid:**
1. Validate all test imports against project dependencies before execution
2. Inject explicit dependency list into LLM prompt
3. Include warning in prompt: "DO NOT hallucinate package names"
4. Parse and validate imports using AST, not regex
**Warning signs:**
- Test imports packages not in pyproject.toml/package.json
- Import errors when running generated tests
- Unfamiliar package names in test files

### Pitfall 2: Ignoring Existing Conventions
**What goes wrong:** Generated tests use different directory/naming than existing tests
**Why it happens:** LLM defaults to common conventions without checking repo-specific patterns
**How to avoid:**
1. Always scan for existing test files first
2. Inject discovered patterns into LLM prompt explicitly
3. Validate generated test paths match pattern
**Warning signs:**
- Test files in new directories when tests/ exists
- Mixing test_*.py and *_test.py patterns
- Tests in src/ when existing tests are in tests/

### Pitfall 3: Framework Mismatch
**What goes wrong:** Generated tests use wrong framework (e.g., unittest when repo uses pytest)
**Why it happens:** LLM defaults to most common framework for language
**How to avoid:**
1. Parse config files to detect framework explicitly
2. Scan existing test imports for framework usage
3. Inject framework name in prompt: "Use pytest, not unittest"
**Warning signs:**
- Test uses unittest.TestCase when config has [tool.pytest]
- Jest syntax in repo using Vitest
- Missing framework-specific fixtures/decorators

### Pitfall 4: Over-Detection in Mixed-Language Repos
**What goes wrong:** Detection picks secondary language or gets confused by vendored code
**Why it happens:** File counting doesn't distinguish main code from dependencies
**How to avoid:**
1. Exclude node_modules, venv, vendor directories from detection
2. Use majority language (50%+ threshold) not plurality
3. Allow manual override in .booty.yml
**Warning signs:**
- Python repo detected as JavaScript (due to node_modules)
- Rust repo detected as C (due to vendored C code)
- Multiple test frameworks detected

### Pitfall 5: No Tests Found → No Conventions
**What goes wrong:** On new repos without tests, detection returns None and LLM has no guidance
**Why it happens:** Pattern inference requires examples, new repos have none
**How to avoid:**
1. Detect language and framework from config even without tests
2. Use language-standard defaults as fallback (but don't hardcode as primary)
3. Let LLM make informed choice based on config
**Warning signs:**
- Generated tests violate language conventions
- Inconsistent naming/structure across multiple PRs
- Test framework changes between PRs

### Pitfall 6: Stale Convention Cache
**What goes wrong:** Cached conventions outdated after repo changes test framework
**Why it happens:** Detection runs once, cached indefinitely
**How to avoid:**
1. Version convention detection (cache includes detector version)
2. Invalidate cache on config file changes
3. Allow manual cache clear via .booty.yml change
**Warning signs:**
- Tests use old framework after migration
- New test directory not recognized
- Pattern mismatch after refactor

## Code Examples

Verified patterns from official sources:

### Python: pytest Test Structure
```python
# Source: https://docs.pytest.org/en/stable/explanation/goodpractices.html
# Standard pytest file naming: test_*.py or *_test.py

# tests/test_user.py
import pytest
from myapp.user import User

def test_user_creation():
    """Test basic user creation (happy path)."""
    user = User(name="Alice", email="alice@example.com")
    assert user.name == "Alice"
    assert user.email == "alice@example.com"

def test_user_invalid_email():
    """Test user creation with invalid email (edge case)."""
    with pytest.raises(ValueError):
        User(name="Bob", email="invalid")

@pytest.fixture
def sample_user():
    """Fixture for reusable test data."""
    return User(name="Test User", email="test@example.com")

def test_user_update(sample_user):
    """Test using fixture."""
    sample_user.update_email("new@example.com")
    assert sample_user.email == "new@example.com"
```

### JavaScript: Jest Test Structure
```javascript
// Source: https://jestjs.io/docs/configuration
// Jest looks for: *.test.js, *.spec.js, or files in __tests__/

// __tests__/user.test.js
import { User } from '../src/user';

describe('User', () => {
  test('creates user with valid data', () => {
    const user = new User('Alice', 'alice@example.com');
    expect(user.name).toBe('Alice');
    expect(user.email).toBe('alice@example.com');
  });

  test('throws on invalid email', () => {
    expect(() => {
      new User('Bob', 'invalid');
    }).toThrow('Invalid email');
  });

  describe('update operations', () => {
    let user;

    beforeEach(() => {
      user = new User('Test', 'test@example.com');
    });

    test('updates email', () => {
      user.updateEmail('new@example.com');
      expect(user.email).toBe('new@example.com');
    });
  });
});
```

### Go: Standard Testing Package
```go
// Source: https://ieftimov.com/posts/testing-in-go-naming-conventions/
// Go test files: *_test.go

// user_test.go
package user

import "testing"

func TestUserCreation(t *testing.T) {
    user := NewUser("Alice", "alice@example.com")

    if user.Name != "Alice" {
        t.Errorf("Expected name Alice, got %s", user.Name)
    }

    if user.Email != "alice@example.com" {
        t.Errorf("Expected email alice@example.com, got %s", user.Email)
    }
}

func TestUserInvalidEmail(t *testing.T) {
    _, err := NewUser("Bob", "invalid")

    if err == nil {
        t.Error("Expected error for invalid email, got nil")
    }
}

func BenchmarkUserCreation(b *testing.B) {
    for i := 0; i < b.N; i++ {
        NewUser("Test", "test@example.com")
    }
}
```

### Rust: Inline Unit Tests
```rust
// Source: https://doc.rust-lang.org/book/ch11-03-test-organization.html
// Rust convention: tests module in same file as code

// src/user.rs
pub struct User {
    pub name: String,
    pub email: String,
}

impl User {
    pub fn new(name: String, email: String) -> Result<User, String> {
        if !email.contains('@') {
            return Err("Invalid email".to_string());
        }
        Ok(User { name, email })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_user_creation() {
        let user = User::new("Alice".to_string(), "alice@example.com".to_string());
        assert!(user.is_ok());

        let user = user.unwrap();
        assert_eq!(user.name, "Alice");
        assert_eq!(user.email, "alice@example.com");
    }

    #[test]
    fn test_invalid_email() {
        let result = User::new("Bob".to_string(), "invalid".to_string());
        assert!(result.is_err());
    }
}
```

### PHP: PHPUnit Test Class
```php
// Source: https://docs.phpunit.de/en/11.5/organizing-tests.html
// PHPUnit: *Test.php files

// tests/UserTest.php
<?php
namespace Tests;

use PHPUnit\Framework\TestCase;
use App\User;

class UserTest extends TestCase
{
    public function testUserCreation(): void
    {
        $user = new User('Alice', 'alice@example.com');

        $this->assertEquals('Alice', $user->getName());
        $this->assertEquals('alice@example.com', $user->getEmail());
    }

    public function testInvalidEmail(): void
    {
        $this->expectException(\InvalidArgumentException::class);
        new User('Bob', 'invalid');
    }

    protected function setUp(): void
    {
        // Runs before each test method
        parent::setUp();
    }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded test patterns | Runtime convention detection | 2025 research consensus | Language-agnostic, adaptable |
| Separate test generation LLM call | Single call with code+tests | Booty architecture decision | Shared context, simpler pipeline |
| Iterative test refinement | One-shot test generation | Booty architecture decision | Tests are spec, not refined |
| Regex import parsing | AST-based import extraction | Python 3.11+ stdlib | Handles edge cases correctly |
| Custom TOML parser | tomllib (stdlib) | Python 3.11 (Oct 2022) | Zero dependencies, battle-tested |
| ML-based language detection | File extension counting | Always standard | Simpler, faster, 99%+ accurate |

**Deprecated/outdated:**
- **toml library**: Deprecated, use tomllib (stdlib) or tomli (backport)
- **GitHub Linguist for detection**: Ruby dependency, GitHub-specific, overkill for local repos
- **Guesslang for language detection**: ML model adds 172MB TensorFlow dependency, 93% accuracy vs 99%+ for extensions

## Open Questions

Things that couldn't be fully resolved:

1. **Mixed-Language Repository Handling**
   - What we know: Some repos have multiple languages (e.g., Python backend + JavaScript frontend)
   - What's unclear: Should detection return multiple language sets, or just primary language?
   - Recommendation: Start with primary language (50%+ of files), add multi-language support in Phase 6 if needed

2. **Convention Cache Invalidation Strategy**
   - What we know: Detection should run once per repo, then cache results
   - What's unclear: When to invalidate cache? Config file change? Time-based? Manual?
   - Recommendation: Version-based cache (include detector version in cache key) + invalidate on config file mtime change

3. **Fallback Behavior When No Framework Detected**
   - What we know: Some repos have no config, no tests, no framework indicators
   - What's unclear: Should LLM pick a framework, or should Booty enforce a default?
   - Recommendation: Let LLM choose based on language + issue context, log decision for user visibility

4. **Test Scope Depth (Happy Path vs Full Coverage)**
   - What we know: Research shows 3 levels (happy path, edge cases, error handling)
   - What's unclear: Should Booty generate all levels, or just happy path + basic edge cases?
   - Recommendation: Start with happy path + basic edge cases (matches 80% coverage from research), avoid over-testing diminishing returns

5. **Import Validation for Non-Python Languages**
   - What we know: Python AST parsing works well for import validation
   - What's unclear: JavaScript/TypeScript/Go/Rust import validation strategies?
   - Recommendation: Start with Python (Booty's current primary use case), add other languages as needed. Tree-sitter could work cross-language.

6. **Test Generation Retry Logic**
   - What we know: Generated tests may have syntax errors, hallucinated imports
   - What's unclear: Should failed test validation trigger LLM retry, or just fail the PR?
   - Recommendation: Log validation errors, include in PR as draft, don't retry test generation (preserves one-shot decision)

## Sources

### Primary (HIGH confidence)
- Python stdlib documentation:
  - [tomllib — Parse TOML files](https://docs.python.org/3/library/tomllib.html)
  - [mimetypes — Map filenames to MIME types](https://docs.python.org/3/library/mimetypes.html)
  - [ast module](https://docs.python.org/3/library/ast.html)
- [pytest — Good Integration Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [Jest — Configuring Jest](https://jestjs.io/docs/configuration)
- [PHPUnit — Organizing Tests](https://docs.phpunit.de/en/11.5/organizing-tests.html)
- [Rust Book — Test Organization](https://doc.rust-lang.org/book/ch11-03-test-organization.html)
- [Go Testing Naming Conventions](https://ieftimov.com/posts/testing-in-go-naming-conventions/)

### Secondary (MEDIUM confidence)
- Research papers (verified with official docs):
  - [CoverUp: Coverage-Guided LLM-Based Test Generation](https://arxiv.org/html/2403.16218v3) - Coverage metrics and iterative approaches
  - [We Have a Package for You! Package Hallucinations](https://arxiv.org/html/2406.10279v3) - 19.7% hallucination rate
  - [Enhancing LLM's Ability to Generate Repository-Aware Unit Tests](https://arxiv.org/html/2501.07425) - Context injection strategies
  - [Understanding Test Convention Consistency](https://dl.acm.org/doi/10.1145/3672448) - 30+ Java test conventions catalog
- Language detection:
  - [Guesslang documentation](https://guesslang.readthedocs.io/) - ML approach (93.45% accuracy)
  - [GitHub enry](https://github.com/src-d/enry) - Linguist port to Go
- Tree-sitter:
  - [AST Parsing at Scale: Tree-sitter Across 40 Languages](https://www.dropstone.io/blog/ast-parsing-tree-sitter-40-languages)
  - [Using Parsers - Tree-sitter](https://tree-sitter.github.io/tree-sitter/using-parsers/)
- Configuration:
  - [Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
  - [linguist/docs/overrides.md](https://github.com/github-linguist/linguist/blob/main/docs/overrides.md)

### Tertiary (LOW confidence)
- WebSearch results on LLM test generation best practices - general strategies, not specific implementations
- Community articles on test naming conventions - patterns confirmed with official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib, well-documented Python tools
- Architecture (convention detection): HIGH - Based on official docs + research consensus
- Architecture (LLM integration): HIGH - Extends existing Booty patterns
- Pitfalls (package hallucination): HIGH - 19.7% rate from peer-reviewed research
- Pitfalls (other): MEDIUM - Inferred from best practices, not project-specific data
- Test scope/coverage: MEDIUM - Research-based, but depends on Booty's goals
- Multi-language handling: LOW - Limited specific research, needs experimentation

**Research date:** 2026-02-15
**Valid until:** ~60 days (stable domain - stdlib, test frameworks change slowly)

**Research gaps addressed:**
- ✅ Language-agnostic detection approach
- ✅ Test framework identification strategies
- ✅ Import validation (anti-hallucination)
- ✅ LLM prompt strategies for test generation
- ✅ Convention inference from existing tests
- ⚠️ Multi-language repo handling (low priority, deferred)
- ⚠️ Non-Python import validation (deferred to implementation)

**Next steps for planning:**
1. Design DetectedConventions Pydantic model
2. Plan detection module structure (detector.py, validator.py)
3. Design cache strategy for conventions
4. Extend existing LLM prompts with test generation
5. Extend CodeGenerationPlan model to include test files
6. Plan import validation integration into generator.py
