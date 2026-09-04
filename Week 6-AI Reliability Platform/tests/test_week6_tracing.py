"""Week 6 — execution tracing tests (uses the existing Flask/SQLAlchemy test
app fixture from tests/conftest.py)."""
import time

from app.observability.tracing import Tracer, NEVER_STORE
from app.models.models import Trace, TraceStep


def test_tracer_persists_a_trace_row(app):
    with app.app_context():
        with Tracer(request_type="chat", model="gemini-3.6-flash", prompt_version="v3",
                     input_text="hello") as t:
            t.set_output("hi there", input_tokens=5, output_tokens=5)
        row = Trace.query.filter_by(trace_id=t.trace_id).first()
        assert row is not None
        assert row.output_text == "hi there"
        assert row.final_outcome == "success"


def test_tracer_records_steps_in_order(app):
    with app.app_context():
        with Tracer(request_type="rag", input_text="q") as t:
            with t.step("retrieval", "semantic_search"):
                time.sleep(0.01)
            with t.step("model_call", "gemini_chat_completion"):
                time.sleep(0.01)
        row = Trace.query.filter_by(trace_id=t.trace_id).first()
        steps = TraceStep.query.filter_by(trace_id=row.id).order_by(TraceStep.seq).all()
        assert [s.name for s in steps] == ["semantic_search", "gemini_chat_completion"]


def test_tracer_marks_failure_on_exception(app):
    with app.app_context():
        try:
            with Tracer(request_type="chat", input_text="boom") as t:
                raise RuntimeError("tool exploded")
        except RuntimeError:
            pass
        row = Trace.query.filter_by(trace_id=t.trace_id).first()
        assert row.final_outcome == "failure"
        assert "RuntimeError" in row.error_status


def test_tracer_never_stores_secrets_in_step_metadata(app):
    with app.app_context():
        with Tracer(request_type="agent", input_text="q") as t:
            with t.step("tool_call", "email_task_summary") as step:
                step.set_meta(api_key="sk-should-not-be-stored", to="user@example.com")
        row = Trace.query.filter_by(trace_id=t.trace_id).first()
        step_row = TraceStep.query.filter_by(trace_id=row.id).first()
        assert "api_key" not in step_row.metadata_dict()
        assert "to" in step_row.metadata_dict()


def test_never_store_list_covers_common_secret_field_names():
    assert "api_key" in NEVER_STORE
    assert "password" in NEVER_STORE
    assert "chain_of_thought" in NEVER_STORE


def test_build_meeting_tools_records_tool_call_trace_steps_when_tracer_given(app):
    from app.observability.tracing import Tracer
    from app.services.agent_service import build_meeting_tools
    from app.models.models import User, TraceStep, db

    with app.app_context():
        user = User(username="tracetool", email="tracetool@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        with Tracer(user_id=user.id, request_type="agent", input_text="create a task") as t:
            tools = build_meeting_tools(user.id, user.email, "meeting",
                                          approved_tools=set(), tracer=t)
            create_fn = next(fn for fn in tools if fn.__name__ == "create_task")
            create_fn("A traced task")

        row = Trace.query.filter_by(trace_id=t.trace_id).first()
        steps = TraceStep.query.filter_by(trace_id=row.id, step_type="tool_call").all()
        assert len(steps) == 1
        assert steps[0].name == "create_task"
        assert steps[0].status == "ok"
