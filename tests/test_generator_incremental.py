"""Tests for Builder incremental code generation."""

from pathlib import Path
from unittest.mock import patch

import pytest

from booty.code_gen.generator import _generate_code_incremental, _is_test_file
from booty.llm.models import FileChange
from booty.planner.schema import HandoffToBuilder, Plan, Step


def test_is_test_file():
    """_is_test_file identifies test paths correctly."""
    assert _is_test_file("tests/test_foo.py") is True
    assert _is_test_file("test_bar.py") is True
    assert _is_test_file("src/foo/test_baz.py") is True
    assert _is_test_file("tests/unit/test_qux.py") is True
    assert _is_test_file("src/booty/main.py") is False
    assert _is_test_file("src/foo.py") is False


def test_generate_code_incremental_calls_generate_single_file_per_step(tmp_path):
    """_generate_code_incremental calls generate_single_file once per add/edit step."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "existing.py").write_text("print('old')\n")

    plan = Plan(
        goal="Add feature X",
        steps=[
            Step(id="P1", action="add", path="src/new_module.py", acceptance="New module created"),
            Step(id="P2", action="edit", path="src/existing.py", acceptance="Existing updated"),
        ],
        handoff_to_builder=HandoffToBuilder(
            branch_name_hint="feat-x",
            commit_message_hint="feat: add X",
            pr_title="Add X",
            pr_body_outline="Summary",
        ),
    )
    file_contents = {"src/existing.py": "print('old')\n"}
    workspace_path = tmp_path

    call_count = 0

    def mock_generate_single_file(*, goal, task_for_file, target_path, operation, **kwargs):
        nonlocal call_count
        call_count += 1
        return FileChange(
            path=target_path,
            content="new content" if operation == "create" else "print('updated')\n",
            operation=operation,
            explanation=f"Step {call_count}",
        )

    with patch("booty.code_gen.generator.generate_single_file", side_effect=mock_generate_single_file):
        result = _generate_code_incremental(
            plan,
            file_contents,
            workspace_path,
            issue_title="Add X",
            issue_body="Body",
            test_conventions_text="",
            limits_constraint="- Max 250 LOC per file",
        )

    assert call_count == 2
    assert len(result.changes) == 2
    assert result.changes[0].path == "src/new_module.py"
    assert result.changes[0].operation == "create"
    assert result.changes[1].path == "src/existing.py"
    assert result.changes[1].operation == "modify"
    assert result.approach
    # Files applied to workspace
    assert (tmp_path / "src" / "new_module.py").read_text() == "new content"
    assert (tmp_path / "src" / "existing.py").read_text() == "print('updated')\n"


def test_generate_code_incremental_classifies_test_files(tmp_path):
    """Test files go to test_files, source files to changes."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()

    plan = Plan(
        goal="Add feature",
        steps=[
            Step(id="P1", action="add", path="src/feature.py", acceptance="Feature module"),
            Step(id="P2", action="add", path="tests/test_feature.py", acceptance="Tests"),
        ],
        handoff_to_builder=HandoffToBuilder(
            branch_name_hint="feat",
            commit_message_hint="feat: add",
            pr_title="Add",
            pr_body_outline="",
        ),
    )

    def mock_generate(*, target_path, operation, **kwargs):
        return FileChange(
            path=target_path,
            content="# code",
            operation=operation,
            explanation="done",
        )

    with patch("booty.code_gen.generator.generate_single_file", side_effect=mock_generate):
        result = _generate_code_incremental(
            plan,
            {},
            tmp_path,
            "Title",
            "Body",
            "",
            limits_constraint="- Max 250 LOC per file",
        )

    assert len(result.changes) == 1
    assert result.changes[0].path == "src/feature.py"
    assert len(result.test_files) == 1
    assert result.test_files[0].path == "tests/test_feature.py"
