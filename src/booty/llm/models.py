"""Pydantic models for LLM structured outputs."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _normalize_path(path: str) -> str:
    """Strip leading slashes from LLM-generated paths to ensure they're relative."""
    return path.lstrip("/")


class IssueAnalysis(BaseModel):
    """Output of issue analysis LLM call."""

    task_description: str = Field(description="Clear description of what needs to be done")
    files_to_modify: list[str] = Field(description="Existing files requiring changes")
    files_to_create: list[str] = Field(description="New files to create")
    files_to_delete: list[str] = Field(
        default_factory=list, description="Files to remove"
    )

    @field_validator("files_to_modify", "files_to_create", "files_to_delete", mode="after")
    @classmethod
    def normalize_paths(cls, v: list[str]) -> list[str]:
        return [_normalize_path(p) for p in v]
    acceptance_criteria: list[str] = Field(
        description="How to verify the changes are correct"
    )
    commit_type: str = Field(
        description="Conventional commit type: feat, fix, refactor, docs, test, chore"
    )
    commit_scope: str | None = Field(default=None, description="Optional commit scope")
    summary: str = Field(description="One-line summary for PR title")


class FileChange(BaseModel):
    """Single file modification from code generation."""

    path: str = Field(description="File path relative to workspace root")

    @field_validator("path", mode="after")
    @classmethod
    def normalize_path(cls, v: str) -> str:
        return _normalize_path(v)
    content: str = Field(description="Complete file content")
    operation: Literal["create", "modify", "delete"] = Field(
        description="Type of file operation"
    )
    explanation: str = Field(
        description="Brief explanation of what changed and why"
    )


class CodeGenerationPlan(BaseModel):
    """Planning step before generation."""

    changes: list[FileChange] = Field(description="All file changes to apply")
    approach: str = Field(description="High-level description of the approach taken")
    testing_notes: str = Field(description="Notes on how to test these changes")
    test_files: list[FileChange] = Field(
        default_factory=list,
        description="Test file changes generated alongside source code"
    )
