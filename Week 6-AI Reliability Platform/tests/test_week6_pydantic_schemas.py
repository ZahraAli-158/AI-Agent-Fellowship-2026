"""Week 6 §49 — Pydantic schemas for the evaluation dataset and tool
arguments (real typed validation, not hand-rolled isinstance() checks)."""
import pytest
from pydantic import ValidationError

from evaluation.schema import EvaluationCase, validate_dataset
from app.guardrails.tool_schemas import (
    CreateTaskArgs, UpdateTaskArgs, TOOL_ARG_MODELS, validate_with_pydantic,
)
from app.guardrails.output import validate_tool_arguments


def test_evaluation_case_accepts_valid_row():
    case = EvaluationCase(test_id="A01", category="A_normal", user_input="hi",
                            expected_behavior="greet back")
    assert case.test_id == "A01"


def test_evaluation_case_rejects_unknown_category():
    with pytest.raises(ValidationError):
        EvaluationCase(test_id="X01", category="not_a_real_category",
                         user_input="hi", expected_behavior="greet")


def test_evaluation_case_rejects_invalid_pass_fail():
    with pytest.raises(ValidationError):
        EvaluationCase(test_id="A01", category="A_normal", user_input="hi",
                         expected_behavior="greet", pass_fail="MAYBE")


def test_validate_dataset_accepts_the_real_dataset():
    from evaluation.runner import load_dataset
    cases = load_dataset()  # raises if any row fails schema validation
    assert len(cases) >= 60


def test_create_task_args_requires_title():
    with pytest.raises(ValidationError):
        CreateTaskArgs()


def test_create_task_args_accepts_title_only():
    args = CreateTaskArgs(title="Buy groceries")
    assert args.title == "Buy groceries"
    assert args.due_date is None


def test_update_task_args_coerces_numeric_string_task_id():
    args = UpdateTaskArgs(task_id="12")
    assert args.task_id == 12


def test_update_task_args_rejects_non_numeric_task_id():
    with pytest.raises(ValidationError):
        UpdateTaskArgs(task_id="abc")


def test_validate_with_pydantic_unknown_tool_passes_through():
    valid, errors = validate_with_pydantic("some_future_tool", {"anything": "goes"})
    assert valid
    assert errors == []


def test_all_meeting_agent_tools_have_a_pydantic_model():
    expected = {"create_task", "list_tasks", "update_task", "complete_task",
                 "delete_task", "email_task_summary", "search_knowledge_base"}
    assert expected.issubset(TOOL_ARG_MODELS.keys())


def test_output_validate_tool_arguments_uses_pydantic_for_create_task():
    result = validate_tool_arguments("create_task", {})
    assert not result.valid
    assert any("title" in e for e in result.errors)


def test_output_validate_tool_arguments_passes_valid_create_task():
    result = validate_tool_arguments("create_task", {"title": "Buy groceries"})
    assert result.valid
