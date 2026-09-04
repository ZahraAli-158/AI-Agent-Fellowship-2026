"""
Week 6 §27 (output guardrails: invalid tool arguments) + §49 (Pydantic
schemas).

Real, typed Pydantic models for every Meeting Agent tool's arguments,
replacing a hand-rolled dict-based schema. Used by
app.guardrails.output.validate_tool_arguments as the actual validation
mechanism — a genuine type/required-field check via Pydantic, not just a
manual isinstance() loop.
"""
from typing import Optional

from pydantic import BaseModel, ValidationError, field_validator


class CreateTaskArgs(BaseModel):
    title: str
    due_date: Optional[str] = None


class ListTasksArgs(BaseModel):
    status_filter: Optional[str] = None


class UpdateTaskArgs(BaseModel):
    task_id: int
    due_date: Optional[str] = None

    @field_validator("task_id", mode="before")
    @classmethod
    def coerce_numeric_string(cls, v):
        # A numeric string (e.g. from a web form field, "12") is fine; a
        # genuinely non-numeric value ("abc") should still fail validation.
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v


class CompleteTaskArgs(BaseModel):
    task_id: int

    @field_validator("task_id", mode="before")
    @classmethod
    def coerce_numeric_string(cls, v):
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v


class DeleteTaskArgs(BaseModel):
    task_id: int

    @field_validator("task_id", mode="before")
    @classmethod
    def coerce_numeric_string(cls, v):
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v


class EmailTaskSummaryArgs(BaseModel):
    subject: str
    body: str
    to_email: Optional[str] = None


class SearchKnowledgeBaseArgs(BaseModel):
    query: str


TOOL_ARG_MODELS = {
    "create_task": CreateTaskArgs,
    "list_tasks": ListTasksArgs,
    "update_task": UpdateTaskArgs,
    "complete_task": CompleteTaskArgs,
    "delete_task": DeleteTaskArgs,
    "email_task_summary": EmailTaskSummaryArgs,
    "search_knowledge_base": SearchKnowledgeBaseArgs,
}


def validate_with_pydantic(tool_name: str, args: dict):
    """Returns (valid: bool, errors: list[str]). Unknown tools pass through
    (nothing to validate against)."""
    model = TOOL_ARG_MODELS.get(tool_name)
    if not model:
        return True, []
    try:
        model(**(args or {}))
        return True, []
    except ValidationError as exc:
        errors = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
        return False, errors
