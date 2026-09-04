"""Week 6 §24/§27 — additional guardrail coverage: unsupported operations
(input) and tool-argument / output-type validation (output)."""
from app.guardrails.input import validate_input, detect_unsupported_operation
from app.guardrails.output import validate_tool_arguments, validate_output_type


def test_unsupported_operation_web_browsing_detected():
    is_unsupported, rule = detect_unsupported_operation("Can you browse the web for me and find prices?")
    assert is_unsupported
    assert rule == "web_browsing"


def test_unsupported_operation_phone_call_detected():
    is_unsupported, rule = detect_unsupported_operation("Please make a phone call to my supervisor.")
    assert is_unsupported


def test_unsupported_operation_blocked_by_validate_input():
    result = validate_input("Can you browse the internet for the latest news?", log=False)
    assert not result.allowed
    assert "unsupported_operation" in result.rule


def test_normal_request_not_flagged_as_unsupported_operation():
    is_unsupported, rule = detect_unsupported_operation("Create a task called 'Buy groceries'.")
    assert not is_unsupported


def test_validate_tool_arguments_flags_missing_required_field():
    result = validate_tool_arguments("create_task", {})
    assert not result.valid
    assert "title" in result.errors[0]


def test_validate_tool_arguments_passes_with_required_field_present():
    result = validate_tool_arguments("create_task", {"title": "Buy groceries"})
    assert result.valid


def test_validate_tool_arguments_flags_wrong_type():
    result = validate_tool_arguments("update_task", {"task_id": "not-a-number", "due_date": "2026-09-01"})
    assert not result.valid


def test_validate_tool_arguments_accepts_numeric_string_for_int_field():
    result = validate_tool_arguments("update_task", {"task_id": "12", "due_date": "2026-09-01"})
    assert result.valid


def test_validate_tool_arguments_unknown_tool_passes_through():
    result = validate_tool_arguments("some_future_tool", {"anything": "goes"})
    assert result.valid


def test_validate_output_type_flags_mismatch():
    result = validate_output_type("just a string", dict, field_name="tool_args")
    assert not result.valid


def test_validate_output_type_passes_on_match():
    result = validate_output_type({"a": 1}, dict, field_name="tool_args")
    assert result.valid
