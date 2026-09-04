"""
Output guardrails (Week 6, Requirement 14).

Validates model output BEFORE it is shown to the user or used to trigger a
tool call. Sensitive/destructive actions must never execute merely because
the LLM generated them — see app.guardrails.permissions.authorize_tool_call
for the actual enforcement choke point; this module is the validation that
runs first.
"""
import re

from app.guardrails.permissions import risk_level_of, requires_approval

URL_RE = re.compile(r"https?://[^\s\)\]]+")


class OutputValidationResult:
    def __init__(self, valid=True, errors=None):
        self.valid = valid
        self.errors = errors or []

    def __bool__(self):
        return self.valid


def validate_structured_output(data: dict, required_fields: list):
    """Generic JSON-schema-lite check: every required field must be present
    and non-null. Returns OutputValidationResult."""
    if not isinstance(data, dict):
        return OutputValidationResult(False, ["Output is not a JSON object."])
    missing = [f for f in required_fields if data.get(f) in (None, "")]
    if missing:
        return OutputValidationResult(False, [f"Missing required field(s): {', '.join(missing)}"])
    return OutputValidationResult(True)


def validate_citations(answer_text: str, retrieved_doc_ids: list, require_citation: bool = False):
    """Checks that a RAG answer cites at least one retrieved source when
    citation is required, and that any bracketed [doc_id] citation actually
    refers to a document that was retrieved (no invented sources)."""
    errors = []
    cited_ids = re.findall(r"\[([\w\.\-]+)\]", answer_text or "")
    if require_citation and not cited_ids:
        errors.append("Answer requires a citation but none was found.")
    known = {str(d) for d in retrieved_doc_ids}
    unknown = [c for c in cited_ids if c not in known]
    if unknown:
        errors.append(f"Citation(s) reference document(s) not in the retrieved set: {unknown}")
    return OutputValidationResult(not errors, errors)


def validate_urls(text: str):
    errors = []
    for url in URL_RE.findall(text or ""):
        if " " in url or url.count("http") > 1:
            errors.append(f"Malformed URL: {url}")
    return OutputValidationResult(not errors, errors)


def validate_tool_action(tool_name: str, approved: bool = False):
    """Blocks a proposed tool action outright if it is high-risk and
    unapproved. Returns OutputValidationResult; does NOT execute the tool."""
    if requires_approval(tool_name) and not approved:
        return OutputValidationResult(
            False, [f"Tool '{tool_name}' ({risk_level_of(tool_name)}) requires approval "
                     f"before execution; refusing to auto-execute."]
        )
    return OutputValidationResult(True)


# Minimal per-tool argument schemas: name -> {param: (required: bool, type)}.
# Kept intentionally small and hand-maintained alongside app.guardrails.permissions.TOOL_RISK
# so the two stay in sync as tools are added.
# Legacy hand-rolled schema, kept only as a fallback for any tool name not
# yet covered by the real Pydantic models in app.guardrails.tool_schemas
# (Week 6 §49 — genuine Pydantic validation is now the primary mechanism).
TOOL_ARG_SCHEMAS = {
    "create_task": {"title": (True, str), "due_date": (False, str)},
    "list_tasks": {"status_filter": (False, str)},
    "update_task": {"task_id": (True, int), "due_date": (False, str)},
    "complete_task": {"task_id": (True, int)},
    "delete_task": {"task_id": (True, int)},
    "email_task_summary": {"subject": (True, str), "body": (True, str), "to_email": (False, str)},
    "search_knowledge_base": {"query": (True, str)},
}


def validate_tool_arguments(tool_name: str, args: dict):
    """Checks a proposed tool call's arguments before execution: required
    parameters present, and present values typed as expected. Primary
    mechanism is the real Pydantic models in app.guardrails.tool_schemas
    (Week 6 §49); the hand-rolled TOOL_ARG_SCHEMAS above is a fallback for
    any tool not yet modeled there. This is separate from
    evaluation.evaluators.deterministic.eval_tool_arguments (which grades
    an evaluation-dataset case against ground truth); this one runs at
    request time against ANY tool call, live or evaluated."""
    from app.guardrails.tool_schemas import TOOL_ARG_MODELS, validate_with_pydantic
    if tool_name in TOOL_ARG_MODELS:
        valid, errors = validate_with_pydantic(tool_name, args)
        return OutputValidationResult(valid, errors)

    schema = TOOL_ARG_SCHEMAS.get(tool_name)
    if not schema:
        return OutputValidationResult(True)  # unknown tool: nothing to validate against
    args = args or {}
    errors = []
    for param, (required, expected_type) in schema.items():
        value = args.get(param)
        if required and value in (None, ""):
            errors.append(f"Missing required argument '{param}' for tool '{tool_name}'.")
            continue
        if value is not None and value != "" and not isinstance(value, expected_type):
            if expected_type is int and isinstance(value, str) and value.isdigit():
                continue
            errors.append(f"Argument '{param}' for tool '{tool_name}' should be {expected_type.__name__}, "
                            f"got {type(value).__name__}.")
    return OutputValidationResult(not errors, errors)


def validate_output_type(value, expected_type, field_name="output"):
    """Checks that a piece of model output is the type the caller actually
    needs (e.g. a tool-call handler expecting a dict got a bare string
    instead) — catches malformed/unexpected output shapes before they're
    used downstream."""
    if not isinstance(value, expected_type):
        return OutputValidationResult(
            False, [f"Expected {field_name} to be {expected_type.__name__}, got {type(value).__name__}."]
        )
    return OutputValidationResult(True)
