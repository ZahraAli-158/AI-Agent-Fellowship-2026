"""
Execution tracing (Week 6, Requirement 7).

Usage:
    from app.observability.tracing import Tracer

    with Tracer(user_id=..., session_id=..., workspace_id=..., request_type="chat",
                model="gemini-3.6-flash", prompt_version="v2", input_text=user_text) as t:
        with t.step("retrieval", "semantic_search"):
            chunks = embedding_service.semantic_search(...)
            t.set_retrieval(chunks, latency_ms=...)

        with t.step("model_call", "gemini_chat_completion"):
            result = gemini_service.chat_completion(...)
            t.set_output(result["text"], result["input_tokens"], result["output_tokens"])

Every request should produce exactly one Trace row plus one TraceStep row per
pipeline stage. Never store API keys, passwords, or private chain-of-thought
in a trace (see NEVER_STORE below) — only the fields Week 6 §17 asks for.
"""
import time
import uuid
import json
import logging

from app.models.models import db, Trace, TraceStep

logger = logging.getLogger("ai_platform.tracing")

# Fields that must never be written into a trace or trace step, even if a
# caller passes them in metadata by mistake.
NEVER_STORE = {"api_key", "gemini_api_key", "password", "password_hash",
                "chain_of_thought", "reasoning", "secret", "token_secret"}


def _scrub(metadata: dict) -> dict:
    return {k: v for k, v in (metadata or {}).items() if k.lower() not in NEVER_STORE}


class Tracer:
    """Context manager producing one Trace row + ordered TraceStep rows."""

    def __init__(self, user_id=None, session_id=None, workspace_id=None,
                 request_type="chat", model="", prompt_version="", input_text="", agent_key=None):
        self.trace_id = uuid.uuid4().hex
        self.user_id = user_id
        self.session_id = session_id
        self.workspace_id = workspace_id
        self.request_type = request_type
        self.agent_key = agent_key
        self.model = model
        self.prompt_version = prompt_version
        self.input_text = (input_text or "")[:4000]
        self._start = None
        self._seq = 0
        self._trace_row = None
        self.output_text = ""
        self.input_tokens = 0
        self.output_tokens = 0
        self.retrieval_latency_ms = 0
        self.retrieved_doc_ids = []
        self.tool_calls = []
        self.error_status = ""
        self.final_outcome = "success"
        self.estimated_cost = 0.0

    def __enter__(self):
        self._start = time.time()
        # Create the Trace row immediately (not at exit) so TraceStep rows
        # recorded during the body have a valid trace_id to reference.
        try:
            row = Trace(
                trace_id=self.trace_id, user_id=self.user_id, session_id=self.session_id,
                workspace_id=self.workspace_id, model=self.model, prompt_version=self.prompt_version,
                request_type=self.request_type, agent_key=self.agent_key, input_text=self.input_text,
            )
            db.session.add(row)
            db.session.commit()
            self._trace_row = row
        except Exception:  # pragma: no cover
            logger.exception("Failed to create trace row %s", self.trace_id)
            db.session.rollback()
        return self

    def step(self, step_type, name):
        return _StepContext(self, step_type, name)

    def set_retrieval(self, doc_ids, latency_ms):
        self.retrieval_latency_ms = latency_ms
        self.retrieved_doc_ids = list(doc_ids or [])

    def add_tool_call(self, tool_name, args, duration_ms, status="ok"):
        self.tool_calls.append({
            "tool": tool_name, "args": _scrub(args or {}),
            "duration_ms": duration_ms, "status": status,
        })

    def set_output(self, text, input_tokens=0, output_tokens=0):
        self.output_text = (text or "")[:4000]
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def set_cost(self, cost):
        self.estimated_cost = cost

    def mark_failure(self, error_status):
        self.error_status = error_status[:120]
        self.final_outcome = "failure"

    def mark_partial(self, note=""):
        self.final_outcome = "partial"
        if note:
            self.error_status = note[:120]

    def __exit__(self, exc_type, exc_val, exc_tb):
        total_latency_ms = int((time.time() - self._start) * 1000)
        if exc_type is not None:
            self.mark_failure(f"{exc_type.__name__}: {exc_val}")

        try:
            row = self._trace_row
            if row is None:
                row = Trace(trace_id=self.trace_id)
                db.session.add(row)
            row.output_text = self.output_text
            row.input_tokens = self.input_tokens
            row.output_tokens = self.output_tokens
            row.total_latency_ms = total_latency_ms
            row.retrieval_latency_ms = self.retrieval_latency_ms
            row.retrieved_doc_ids = json.dumps(self.retrieved_doc_ids)
            row.tool_calls = json.dumps(self.tool_calls)
            row.error_status = self.error_status
            row.final_outcome = self.final_outcome
            row.estimated_cost = self.estimated_cost
            db.session.commit()
            self._trace_row = row
        except Exception:  # pragma: no cover - tracing must never break the request
            logger.exception("Failed to persist trace %s", self.trace_id)
            db.session.rollback()

        # Swallow nothing — let the original exception (if any) propagate.
        return False

    def _record_step(self, step_type, name, status, duration_ms, metadata):
        self._seq += 1
        try:
            db.session.add(TraceStep(
                trace_id=self._trace_row.id if self._trace_row else None,
                seq=self._seq, step_type=step_type, name=name, status=status,
                duration_ms=duration_ms, metadata_json=json.dumps(_scrub(metadata)),
            ))
            # Steps are flushed together with the Trace commit at __exit__ if
            # the trace row doesn't exist yet; otherwise commit immediately.
            if self._trace_row:
                db.session.commit()
        except Exception:  # pragma: no cover
            logger.exception("Failed to persist trace step %s/%s", self.trace_id, name)
            db.session.rollback()


class _StepContext:
    """Times a single pipeline stage and records it against the parent Tracer."""

    def __init__(self, tracer: Tracer, step_type, name):
        self.tracer = tracer
        self.step_type = step_type
        self.name = name
        self.metadata = {}
        self._start = None
        self.status = "ok"

    def set_meta(self, **kwargs):
        self.metadata.update(kwargs)

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.time() - self._start) * 1000)
        if exc_type is not None:
            self.status = "failed"
            self.metadata["error"] = f"{exc_type.__name__}: {exc_val}"
        self.tracer._record_step(self.step_type, self.name, self.status, duration_ms, self.metadata)
        return False  # never swallow exceptions
