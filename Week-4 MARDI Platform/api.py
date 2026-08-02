"""
FastAPI backend — REST API layer over the existing LangGraph multi-agent
workflow (app/agents, app/graph, app/tools, app/schemas are untouched;
this module only exposes them over HTTP).

Design notes:
  - Each workflow run executes on its own background thread via
    `graph.stream(..., stream_mode="values")`, which yields the FULL merged
    WorkflowState after every node/superstep. Each snapshot is stored on an
    in-memory RunSession, which is what every GET endpoint below reads from
    — this is what makes "Live workflow status" possible without polling
    the graph internals directly.
  - Human checkpoints (Requirement 12) are implemented with a
    threading.Event: the `human_review_callback` given to the graph blocks
    the background thread until POST /api/runs/{id}/checkpoint resolves it.
    This reuses the exact same `app/graph/human.py` contract already built
    and tested for the CLI — no workflow logic is duplicated here.
  - State is in-memory only (SESSIONS dict) — fine for a single-process
    dev/demo server. Swapping in a real datastore would only touch this
    file, not the agents/graph/tools/schemas layer.
"""
from __future__ import annotations

import json
import threading
import time
import traceback
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agents import supervisor as supervisor_agent
from app.graph import human
from app.graph.state import new_state
from app.graph.workflow import build_workflow
from app.observability.logging_config import get_logger
from app.observability.tracer import summarize_run
from app.schemas.tasks import AgentRole
from app.config import settings

logger = get_logger(__name__)

app = FastAPI(title="MARDI — Multi-Agent Research & Decision Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev server only — tighten this for real deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# In-memory run session
# --------------------------------------------------------------------------

class RunSession:
    def __init__(self, run_id: str, user_request: str, max_revisions: int):
        self.run_id = run_id
        self.user_request = user_request
        self.max_revisions = max_revisions
        self.state: Dict[str, Any] = {}
        self.status: str = "starting"  # starting | running | awaiting_human | finished | error
        self.pending_checkpoint: Optional[Dict[str, Any]] = None
        self.decision_event = threading.Event()
        self.decision_response: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at: float = time.time()
        self.finished_at: Optional[float] = None

    def summary(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "user_request": self.user_request,
            "status": self.status,
            "workflow_status": self.state.get("workflow_status"),
            "created_at": self.created_at,
            "elapsed_s": round((self.finished_at or time.time()) - self.created_at, 2),
            "evidence_count": len(self.state.get("evidence", [])),
            "revision_count": self.state.get("revision_count", 0),
            "has_report": self.state.get("final_report") is not None,
        }


SESSIONS: Dict[str, RunSession] = {}


def _api_callback(session: RunSession):
    """Adapts app/graph/human.py's HumanCallback contract to block a
    background thread until the frontend resolves it via POST /checkpoint.
    """

    def callback(checkpoint_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        session.pending_checkpoint = {"name": checkpoint_name, "payload": payload}
        session.status = "awaiting_human"
        session.decision_event.clear()
        session.decision_event.wait()  # blocks here until the API sets it
        session.pending_checkpoint = None
        session.status = "running"
        response = session.decision_response or {}
        session.decision_response = None
        return response

    return callback


_TERMINAL_WORKFLOW_STATUSES = {"completed", "failed"}


def _run_graph(session: RunSession) -> None:
    logger.info("[run %s] starting workflow thread for request: %r", session.run_id, session.user_request)
    try:
        session.status = "running"
        graph = build_workflow(_api_callback(session))
        initial_state = new_state(session.run_id, session.user_request, session.max_revisions)
        for state in graph.stream(initial_state, config={"recursion_limit": 60}, stream_mode="values"):
            session.state = state
            logger.debug("[run %s] state update -> workflow_status=%s", session.run_id, state.get("workflow_status"))
        session.status = "finished"
        logger.info("[run %s] finished with status=%s", session.run_id, session.state.get("workflow_status"))
    except Exception as exc:  # noqa: BLE001
        session.error = f"{exc}\n{traceback.format_exc()}"
        session.status = "error"
        logger.error("[run %s] ERROR: %s", session.run_id, session.error)
    finally:
        # Safety net (workflows must always reach a final state): no matter
        # how the thread above exited — a clean stream finish, an uncaught
        # exception from a node, or a crash mid-node — the run must never
        # sit in a non-terminal workflow_status forever. Every individual
        # agent already sets workflow_status=FAILED on its own known
        # failure paths; this only catches whatever is left over (e.g. an
        # unexpected exception) so the UI never shows an indefinite
        # "researching"/"analyzing" spinner.
        if session.state.get("workflow_status") not in _TERMINAL_WORKFLOW_STATUSES:
            session.state["workflow_status"] = "failed"
            if session.error is None:
                session.error = "Workflow ended unexpectedly without completing. Marked as failed."
        # Never leave the frontend blocked on a checkpoint dialog for a run
        # that is no longer progressing.
        session.pending_checkpoint = None
        session.decision_event.set()
        session.finished_at = time.time()


_TERMINAL_STATUSES = {"completed", "failed"}


def _last_active_status(state: Dict[str, Any]) -> Optional[str]:
    """Scans the trace for the most recent status_change event that isn't
    itself a terminal one, so a run that fails can still report which
    stage it actually reached (e.g. 'analyzing_request') rather than the
    frontend having to assume 'failed' means everything up to that point
    finished. `workflow_status` alone only ever holds the CURRENT status,
    not the history, once the graph has moved past a stage."""
    for event in reversed(state.get("trace", [])):
        if event.get("type") == "status_change" and event.get("status") not in _TERMINAL_STATUSES:
            return event["status"]
    return None


def _get_session(run_id: str) -> RunSession:
    session = SESSIONS.get(run_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return session


def _jsonable(obj: Any) -> Any:
    """Converts Pydantic models (Task, Evidence, AnalysisOutput, ...) nested
    inside the raw WorkflowState into plain JSON-safe structures."""

    def default(o):
        if hasattr(o, "model_dump"):
            return o.model_dump(mode="json")
        return str(o)

    return json.loads(json.dumps(obj, default=default))


# --------------------------------------------------------------------------
# Request/response schemas
# --------------------------------------------------------------------------

class AnalyzeRequestBody(BaseModel):
    user_request: str


class StartRunBody(BaseModel):
    user_request: str
    max_revisions: int = 2


class CheckpointDecisionBody(BaseModel):
    decision: Optional[str] = None  # "approve" | "edit" | "reject" | "request_changes"
    answers: Optional[List[str]] = None  # for the clarification checkpoint
    # Edit & Continue (checkpoint 1) — all optional, only used when decision == "edit"
    research_objective: Optional[str] = None  # edited objective text
    task_edits: Optional[List[Dict[str, str]]] = None  # [{"id": "R2", "description": "..."}, ...]
    additional_instructions: Optional[str] = None


# --------------------------------------------------------------------------
# 1. Request Analysis (standalone preview, before committing to a full run)
# --------------------------------------------------------------------------

@app.post("/api/requests/analyze")
def analyze_request(body: AnalyzeRequestBody):
    """Runs ONLY the Supervisor's request-analysis step and returns the
    structured objective — lets the frontend show the Request Analysis
    screen before the user commits to a full (costly) workflow run."""
    probe_state = new_state(run_id="preview", user_request=body.user_request)
    result = supervisor_agent.analyze_request(probe_state)
    return _jsonable(result)


# --------------------------------------------------------------------------
# 2. Workflow Execution
# --------------------------------------------------------------------------

@app.post("/api/runs")
def start_run(body: StartRunBody):
    run_id = f"RUN-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    session = RunSession(run_id, body.user_request, body.max_revisions)
    SESSIONS[run_id] = session
    thread = threading.Thread(target=_run_graph, args=(session,), daemon=True)
    thread.start()
    return {"run_id": run_id, "status": session.status}


# --------------------------------------------------------------------------
# 3. Live Workflow Status
# --------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/status")
def get_status(run_id: str):
    session = _get_session(run_id)
    state = session.state
    return {
        "run_id": run_id,
        "session_status": session.status,
        "workflow_status": state.get("workflow_status"),
        "last_active_status": _last_active_status(state),
        "user_request": session.user_request,
        "research_objective": _jsonable(state.get("research_objective", {})),
        "revision_count": state.get("revision_count", 0),
        "max_revisions": state.get("max_revisions", session.max_revisions),
        "evidence_count": len(state.get("evidence", [])),
        "error_count": len(state.get("errors", [])),
        "checkpoint_1_status": state.get("checkpoint_1_status"),
        "checkpoint_2_status": state.get("checkpoint_2_status"),
        "pending_checkpoint": session.pending_checkpoint,
        "error": session.error,
        "elapsed_s": round((session.finished_at or time.time()) - session.created_at, 2),
    }


# --------------------------------------------------------------------------
# 4. Task Plan
# --------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/tasks")
def get_tasks(run_id: str):
    session = _get_session(run_id)
    state = session.state
    task_plan = state.get("task_plan", [])
    completed = set(state.get("completed_tasks", []))

    # Derive a live "running" status per task from trace agent_start/agent_end
    # events, since Task.status itself is only set to completed at plan-time
    # for R1 — everything else is tracked via completed_tasks + trace.
    running_agents = set()
    for e in state.get("trace", []):
        if e["type"] == "agent_start":
            running_agents.add(e["agent"])
        elif e["type"] == "agent_end":
            running_agents.discard(e["agent"])

    def agent_label(task) -> str:
        role = task.assigned_agent if isinstance(task.assigned_agent, str) else task.assigned_agent.value
        if role == AgentRole.RESEARCHER.value and task.parameters.get("target"):
            return f"Researcher-{task.parameters['target']}"
        return role

    tasks_out = []
    for t in task_plan:
        tid = t.id
        if tid in completed:
            status = "completed"
        elif agent_label(t) in running_agents:
            status = "running"
        else:
            status = "pending"
        d = _jsonable(t)
        d["live_status"] = status
        tasks_out.append(d)

    return {"tasks": tasks_out, "completed_count": len(completed), "total_count": len(task_plan)}


# --------------------------------------------------------------------------
# 5. Evidence
# --------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/evidence")
def get_evidence(run_id: str):
    from app.tools.evidence import summarize_evidence_counts

    session = _get_session(run_id)
    evidence = session.state.get("evidence", [])
    return {
        "evidence": _jsonable(evidence),
        "count": len(evidence),
        "summary": summarize_evidence_counts(evidence),
    }


# --------------------------------------------------------------------------
# 6. Execution Logs (trace)
# --------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/trace")
def get_trace(run_id: str):
    session = _get_session(run_id)
    trace = session.state.get("trace", [])
    return {
        "trace": trace,
        "summary": summarize_run(run_id, trace) if trace else None,
    }


# --------------------------------------------------------------------------
# 7. Final Report
# --------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/report")
def get_report(run_id: str):
    session = _get_session(run_id)
    report = session.state.get("final_report")
    if report is None:
        return {"available": False}
    return {
        "available": True,
        "report": _jsonable(report),
        "markdown": report.to_markdown(),
    }


# --------------------------------------------------------------------------
# 8. Human Checkpoint Approvals
# --------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/checkpoint")
def get_pending_checkpoint(run_id: str):
    session = _get_session(run_id)
    return {"pending": session.pending_checkpoint}


@app.post("/api/runs/{run_id}/checkpoint")
def resolve_checkpoint(run_id: str, body: CheckpointDecisionBody):
    session = _get_session(run_id)
    if session.pending_checkpoint is None:
        raise HTTPException(status_code=400, detail="No pending checkpoint for this run")

    decision_map = {"approve": "approved", "edit": "edited", "reject": "rejected", "request_changes": "request_changes"}
    response: Dict[str, Any] = {}
    if body.answers is not None:
        response["answers"] = body.answers
    if body.decision is not None:
        response["decision"] = decision_map.get(body.decision, body.decision)
    if body.research_objective is not None:
        response["research_objective"] = body.research_objective
    if body.task_edits is not None:
        response["task_edits"] = body.task_edits
    if body.additional_instructions is not None:
        response["additional_instructions"] = body.additional_instructions

    session.decision_response = response
    session.decision_event.set()
    return {"ok": True}


# --------------------------------------------------------------------------
# 9. Workflow State (full state inspector)
# --------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/state")
def get_state(run_id: str):
    session = _get_session(run_id)
    return _jsonable(session.state)


# --------------------------------------------------------------------------
# 10. Run History
# --------------------------------------------------------------------------

@app.get("/api/runs")
def list_runs():
    return sorted((s.summary() for s in SESSIONS.values()), key=lambda r: r["created_at"], reverse=True)


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_mode": settings.resolved_llm_mode(), "llm_provider": settings.llm_provider}
