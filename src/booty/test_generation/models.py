"""Data models for test generation."""

from pydantic import BaseModel, Field


class DetectedConventions(BaseModel):
    """Detected test conventions for a repository.

    This model captures language-agnostic test conventions inferred from
    repository structure, config files, and existing tests.
    """

    language: str = Field(
        description="Primary language: python, go, javascript, typescript, rust, php, ruby, java, cpp, c, or unknown"
    )

    test_framework: str | None = Field(
        default=None,
        description="Detected test framework: pytest, unittest, jest, vitest, go test, cargo test, phpunit, etc."
    )

    test_directory: str | None = Field(
        default=None,
        description="Inferred test directory: tests, test, __tests__, spec, etc."
    )

    test_file_pattern: str | None = Field(
        default=None,
        description="Inferred naming pattern: test_*.py, *.test.js, *_test.go, etc."
    )

    config_file: str | None = Field(
        default=None,
        description="Path to config file found (pyproject.toml, package.json, etc.)"
    )

    existing_test_examples: list[str] = Field(
        default_factory=list,
        description="Up to 3 sample test file paths for reference"
    )

    def format_for_prompt(self) -> str:
        """Format detected conventions as context for LLM prompt.

        This is injected into code generation prompts to guide test generation
        according to repository conventions.

        Returns:
            Formatted string with test generation requirements
        """
        parts = [
            "## Test Generation Requirements",
            "",
            "Generate unit tests alongside code changes following these repository conventions:",
            "",
            f"**Language:** {self.language}",
        ]

        if self.test_framework:
            parts.append(f"**Test Framework:** {self.test_framework}")
        else:
            parts.append("**Test Framework:** Unknown - infer appropriate framework for the language")

        if self.test_directory:
            parts.append(f"**Test Directory:** {self.test_directory}/")
        else:
            parts.append("**Test Directory:** No existing tests - choose conventional location for the language")

        if self.test_file_pattern:
            parts.append(f"**Test File Naming:** {self.test_file_pattern}")
        else:
            parts.append("**Test File Naming:** No existing tests - follow standard naming conventions for the language")

        parts.extend([
            "",
            "**CRITICAL:** Use ONLY imports that exist in the project dependencies.",
            "DO NOT hallucinate package names or import paths.",
            "Verify all test imports match the detected framework and project structure.",
            "Check pyproject.toml, package.json, or other config files for available dependencies.",
        ])

        if self.existing_test_examples:
            parts.extend([
                "",
                "**Example Test Files (for reference):**",
            ])
            for example in self.existing_test_examples[:2]:  # Max 2 examples in prompt
                parts.append(f"- {example}")

        return "\n".join(parts)
