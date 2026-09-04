"""
Week 6 §9 (dataset schema) + §49 (Pydantic schemas).

A typed, validated schema for every row in evaluation/dataset.jsonl,
matching §9's required fields exactly. `evaluation/generate_dataset.py`
validates every case against this model before writing the file, and
`evaluation/runner.py` validates every row on load, so a malformed dataset
row fails loudly and early rather than causing a confusing downstream
evaluator crash.
"""
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

VALID_CATEGORIES = {
    "A_normal", "B_difficult", "C_ambiguous", "D_tool_use", "E_knowledge_rag", "F_adversarial",
}


class EvaluationCase(BaseModel):
    """One row of evaluation/dataset.jsonl — Week 6 §9's required schema:
    Test ID, Category, User Input, Expected Behavior, Expected Tool,
    Expected Source, Expected Structured Output, Approval Required,
    Critical Failure Conditions, Actual Result, Score, Pass/Fail, Notes."""

    test_id: str = Field(..., min_length=1, description="Unique test case identifier, e.g. 'A01'.")
    category: str
    user_input: str = Field(..., min_length=1)
    expected_behavior: str = Field(..., min_length=1)
    expected_tool: Optional[str] = None
    expected_source: Optional[Any] = None  # list[str] for RAG cases, or None
    expected_structured_output: Optional[dict] = None
    approval_required: bool = False
    critical_failure_conditions: list[str] = Field(default_factory=list)

    # Filled in after a run (Week 6 §9's "results" columns) — absent/None
    # until evaluation/runner.py populates them.
    actual_result: Optional[str] = None
    score: Optional[float] = None
    pass_fail: Optional[str] = None
    failure_code: Optional[str] = None
    notes: str = ""

    @field_validator("category")
    @classmethod
    def category_must_be_known(cls, v):
        if v not in VALID_CATEGORIES:
            raise ValueError(f"Unknown category '{v}' — must be one of {sorted(VALID_CATEGORIES)}")
        return v

    @field_validator("pass_fail")
    @classmethod
    def pass_fail_must_be_valid(cls, v):
        if v is not None and v not in ("PASS", "FAIL"):
            raise ValueError(f"pass_fail must be 'PASS', 'FAIL', or None, got {v!r}")
        return v


def validate_dataset(cases: list[dict]) -> list[EvaluationCase]:
    """Validates a full loaded dataset; raises pydantic.ValidationError with
    a clear message pointing at the offending row if anything is malformed."""
    return [EvaluationCase(**c) for c in cases]
