"""
Supervisor / Orchestrator Agent — Agent 1 (Section 5).

Responsibilities implemented here:
  - Request Analysis (Requirement 1)
  - Clarification Handling (Requirement 2)
  - Dynamic Planning (Requirement 3)
  - Workflow status tracking / completion decisions

The Supervisor deliberately does NOT call the search tool or write
evidence — it only reads aggregate state (task_plan, critic_feedback,
evidence counts) to decide what happens next. See the tool permission
matrix in docs/agent_design_spec.md.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.config import settings
from app.graph.state import WorkflowState, WorkflowStatus, CheckpointStatus
from app.observability import tracer
from app.observability.logging_config import get_logger
from app.schemas.tasks import AgentRole, Priority, Task, TaskStatus
from app.services.llm_client import llm_client

AGENT_ID = "Supervisor"
logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are the Supervisor agent in a multi-agent research system. You NEVER "
    "perform research yourself. Given a user's request, extract a structured "
    "objective (main objective, 3-5 sub-questions, evaluation criteria, "
    "constraints, missing information) and respond ONLY as JSON with keys: "
    "objective, sub_questions (list), evaluation_criteria (list), constraints (list), "
    "missing_information (list), needs_clarification (bool), clarification_questions (list). "
    "IMPORTANT: 'objective' MUST be a single plain string sentence, never a nested object. "
    "'sub_questions' and 'evaluation_criteria' MUST be flat lists of plain strings."
)


def _coerce_objective_fields(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Defensive normalization for live-LLM output that doesn't strictly follow
    the requested flat schema — prevents a malformed 'objective' (e.g. a
    nested object) from silently rendering as "[object Object]" downstream
    in the dashboard, or a non-list 'sub_questions'/'evaluation_criteria'
    from breaking frontend code that expects to .map() over them."""
    obj = parsed.get("objective")
    if not isinstance(obj, str):
        parsed["objective"] = json.dumps(obj) if obj is not None else ""
    for list_field in ("sub_questions", "evaluation_criteria", "constraints", "missing_information", "clarification_questions"):
        value = parsed.get(list_field)
        if value is None:
            parsed[list_field] = []
        elif not isinstance(value, list):
            parsed[list_field] = [str(value)]
        else:
            parsed[list_field] = [v if isinstance(v, str) else json.dumps(v) for v in value]
    return parsed

# A tiny, explicit mapping used by both the mock LLM path and as a sanity
# fallback in live mode — this is what makes planning *depend on the
# request* rather than being a hard-coded fixed sequence (Requirement 3).
_TOPIC_CANDIDATES = {
    "framework": ("agent_frameworks", ["LangGraph", "CrewAI", "OpenAI Agents SDK"]),
    "agent": ("agent_frameworks", ["LangGraph", "CrewAI", "OpenAI Agents SDK"]),
    "cloud": ("cloud_platforms", ["AWS", "Google Cloud", "Azure"]),
    "coding assistant": ("agent_frameworks", ["LangGraph", "CrewAI", "OpenAI Agents SDK"]),
    # RAG / retrieval-augmented-generation requests have their own corpus
    # topic (app/storage/corpus/rag_enterprise_chatbots.json) — without this,
    # any RAG-related request fell through to the generic "Option A/B/C"
    # placeholders below, which never match anything in the corpus and
    # guaranteed a missing_evidence failure for every such request.
    "retrieval-augmented": ("rag_enterprise_chatbots", ["Vector-Search RAG", "Hybrid Retrieval RAG", "Fine-Tuned Model (No RAG)"]),
    "retrieval augmented": ("rag_enterprise_chatbots", ["Vector-Search RAG", "Hybrid Retrieval RAG", "Fine-Tuned Model (No RAG)"]),
    "chatbot": ("rag_enterprise_chatbots", ["Vector-Search RAG", "Hybrid Retrieval RAG", "Fine-Tuned Model (No RAG)"]),
}

_RAG_WORD_RE = re.compile(r"\brag\b")


def _detect_topic(user_request: str) -> tuple[str, List[str]]:
    lowered = user_request.lower()
    if _RAG_WORD_RE.search(lowered):
        return "rag_enterprise_chatbots", ["Vector-Search RAG", "Hybrid Retrieval RAG", "Fine-Tuned Model (No RAG)"]
    for keyword, (topic, candidates) in _TOPIC_CANDIDATES.items():
        if keyword in lowered:
            return topic, candidates
    # Generic fallback — still request-dependent (uses the request's own
    # nouns as placeholders) rather than one single hard-coded plan.
    # NOTE: by design this has zero corpus coverage (see
    # docs/known_limitations.md) and is expected to end in a clean
    # missing_evidence FAILED status rather than a fabricated report.
    return "general", ["Option A", "Option B", "Option C"]


def _extract_json_object(text: str) -> str:
    """Best-effort recovery for a live LLM response that isn't pure JSON —
    e.g. leading/trailing prose despite the system prompt insisting on
    JSON-only output. Takes the substring between the first '{' and the
    last '}' rather than assuming the whole response body is already
    clean JSON, so a stray sentence around the object doesn't turn an
    otherwise-valid response into a hard parse failure.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _mock_analyze(user_request: str) -> str:
    lowered = user_request.lower()
    topic, candidates = _detect_topic(user_request)
    is_vague = len(user_request.split()) < 6 and "compare" not in lowered and "research" not in lowered

    payload = {
        "objective": user_request.strip().rstrip(".") + ".",
        "sub_questions": [
            f"What are the available options ({', '.join(candidates)})?",
            "What are their strengths?",
            "What are their limitations?",
            "Which is best for the stated use case?",
        ],
        "evaluation_criteria": ["Development complexity", "Reliability", "Tool support", "State management", "Production readiness"],
        "constraints": [],
        "missing_information": [] if not is_vague else ["Target use case", "Team size", "Prototype vs production"],
        "needs_clarification": is_vague,
        "clarification_questions": (
            []
            if not is_vague
            else [
                "What use case is this for?",
                "Is this for a prototype or a production system?",
                "Any language or ecosystem constraints (Python vs JavaScript)?",
            ]
        ),
        "_topic": topic,
        "_candidates": candidates,
    }
    return json.dumps(payload)


def analyze_request(state: WorkflowState) -> Dict[str, Any]:
    """Node: Request Analysis + Clarification detection (Requirements 1 & 2)."""
    trace: List[Dict[str, Any]] = [tracer.agent_start(AGENT_ID)]

    if not state.get("user_request", "").strip():
        trace.append(tracer.error(AGENT_ID, "empty_request", "user_request is empty or whitespace-only"))
        trace.append(tracer.status_change(WorkflowStatus.FAILED))
        logger.error("run %s: empty_request — cannot analyze an empty request", state.get("run_id"))
        return {
            "errors": [{"agent": AGENT_ID, "type": "empty_request", "detail": "Cannot analyze an empty request"}],
            "workflow_status": WorkflowStatus.FAILED,
            "trace": trace,
        }

    # A live LLM call can fail two structurally different ways: the
    # transport/API call itself errors out (already retried once inside
    # llm_client.complete via TOOL_MAX_RETRIES), OR the call succeeds but
    # returns text that isn't valid JSON — e.g. truncated mid-array because
    # a detailed multi-criteria request (compliance + cost + scalability +
    # AI model support, in the healthcare-cloud example) produces a longer
    # structured answer than a tighter token budget allows, or the model
    # wraps the object in a stray sentence despite the system prompt.
    # Previously only the first failure mode was retried; a malformed-but-
    # successfully-returned response failed permanently on the very first
    # attempt, before create_plan ever ran. This loop treats both failure
    # modes the same way: retry the whole call, up to the same configured
    # budget, before giving up.
    parsed: Optional[Dict[str, Any]] = None
    last_error_type = "model_api_failure"
    last_error_detail = "unknown error"
    for _ in range(settings.tool_max_retries + 1):
        result = llm_client.complete(
            system=SYSTEM_PROMPT,
            user=state["user_request"],
            mock_fn=lambda: _mock_analyze(state["user_request"]),
            max_tokens=2000,
        )
        if result.error:
            last_error_type, last_error_detail = "model_api_failure", result.error
            continue
        try:
            parsed = json.loads(_extract_json_object(result.text))
            break
        except json.JSONDecodeError as exc:
            last_error_type, last_error_detail = "invalid_structured_output", str(exc)
            continue

    if parsed is None:
        trace.append(tracer.error(AGENT_ID, last_error_type, last_error_detail))
        trace.append(tracer.status_change(WorkflowStatus.FAILED))
        logger.error(
            "run %s: analyze_request failed after retries — type=%s detail=%s",
            state.get("run_id"), last_error_type, last_error_detail,
        )
        return {
            "errors": [{"agent": AGENT_ID, "type": last_error_type, "detail": last_error_detail}],
            "workflow_status": WorkflowStatus.FAILED,
            "trace": trace,
        }

    # Coerce any malformed fields (e.g. a live LLM returning 'objective' as a
    # nested object instead of a plain string) into safe, renderable values
    # before this dict is stored in state and shown on the dashboard.
    parsed = _coerce_objective_fields(parsed)

    # Dynamic Planning (Requirement 3) must not silently depend on the live
    # LLM happening to echo back internal "_topic"/"_candidates" fields —
    # a real model has no reason to know about our local corpus's naming.
    # Topic/candidate detection is therefore always computed deterministically
    # here, in both mock AND live mode, then merged into the parsed objective.
    topic, candidates = _detect_topic(state["user_request"])
    parsed["_topic"] = topic
    parsed["_candidates"] = candidates

    needs_clarification = parsed.get("needs_clarification", False)
    trace.append(tracer.agent_end(AGENT_ID))
    trace.append(tracer.status_change(
        WorkflowStatus.AWAITING_CLARIFICATION if needs_clarification else WorkflowStatus.ANALYZING_REQUEST
    ))

    return {
        "research_objective": parsed,
        "needs_clarification": needs_clarification,
        "clarification_questions": parsed.get("clarification_questions", []),
        "workflow_status": (
            WorkflowStatus.AWAITING_CLARIFICATION if needs_clarification else WorkflowStatus.ANALYZING_REQUEST
        ),
        "trace": trace,
    }


def create_plan(state: WorkflowState) -> Dict[str, Any]:
    """Node: Dynamic Planning (Requirement 3).

    Builds the task plan directly from research_objective's sub-questions
    and detected candidates — NOT a fixed hard-coded sequence. Different
    requests produce a different number of research tasks / different
    assigned research targets.
    """
    trace: List[Dict[str, Any]] = [tracer.agent_start(AGENT_ID)]
    objective = state["research_objective"]
    candidates: List[str] = objective.get("_candidates", ["Option A", "Option B", "Option C"])

    tasks: List[Task] = [
        Task(
            id="R1",
            description="Identify candidate options and confirm scope",
            assigned_agent=AgentRole.SUPERVISOR,
            dependencies=[],
            status=TaskStatus.COMPLETED,
            priority=Priority.HIGH,
            completed_at="now",
        )
    ]
    research_ids = []
    for i, candidate in enumerate(candidates, start=1):
        rid = f"R{i + 1}"
        research_ids.append(rid)
        tasks.append(
            Task(
                id=rid,
                description=f"Research {candidate}",
                assigned_agent=AgentRole.RESEARCHER,
                dependencies=["R1"],
                status=TaskStatus.PENDING,
                priority=Priority.HIGH,
                parameters={
                    "target": candidate,
                    "topic": objective.get("_topic", "general"),
                    # Only the first research task also checks cross-cutting
                    # reliability/production-readiness evidence, so the
                    # comparison as a whole surfaces that gap exactly once.
                    "also_check_reliability": i == 1,
                },
            )
        )
    tasks.append(Task(id="A1", description="Compare findings", assigned_agent=AgentRole.ANALYST,
                       dependencies=research_ids, priority=Priority.HIGH))
    tasks.append(Task(id="C1", description="Review evidence and reasoning", assigned_agent=AgentRole.CRITIC,
                       dependencies=["A1"], priority=Priority.HIGH))
    tasks.append(Task(id="W1", description="Generate final report", assigned_agent=AgentRole.WRITER,
                       dependencies=["C1"], priority=Priority.MEDIUM))

    trace.append(tracer.agent_end(AGENT_ID))
    trace.append(tracer.status_change(WorkflowStatus.AWAITING_PLAN_APPROVAL))

    return {
        "task_plan": tasks,
        "completed_tasks": ["R1"],
        "workflow_status": WorkflowStatus.AWAITING_PLAN_APPROVAL,
        "checkpoint_1_status": CheckpointStatus.WAITING,
        "trace": trace,
    }


def decide_after_critic(state: WorkflowState) -> Dict[str, Any]:
    """Node: sits between Critic and the routing decision. Increments
    revision_count only when actually looping back for another revision —
    this is what guarantees the quality-control loop terminates
    (Requirement 10) while still letting every configured revision cycle
    actually happen.

    IMPORTANT: whether to route to "analyst" or "writer" next must NOT be
    re-derived from comparing the (now-incremented) revision_count against
    max_revisions again in routing.py — doing that caused an off-by-one
    where the last allowed cycle got vetoed the instant the counter reached
    max_revisions, before the Analyst ever got to use it (e.g.
    max_revisions=1 silently behaved like max_revisions=0). Instead, this
    function sets `revision_forced_stop` explicitly, and routing.py trusts
    it directly.
    """
    feedback = state.get("critic_feedback")
    if feedback is None:
        # Defensive guard: should not normally be reached because
        # routing.route_after_critic already short-circuits to END when the
        # Critic failed to produce feedback, but this keeps the node itself
        # safe against ever being invoked without it instead of crashing.
        return fail_workflow("Critic did not produce feedback; cannot decide next step")
    decision = feedback.decision if isinstance(feedback.decision, str) else feedback.decision.value
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 2)

    if decision == "approved":
        return {"trace": [tracer.status_change(WorkflowStatus.WRITING_REPORT)], "revision_forced_stop": False}

    if revision_count >= max_revisions:
        trace = [tracer.revision(revision_count, max_revisions, "max_revisions_reached_forced_termination")]
        return {"trace": trace, "revision_forced_stop": True}

    new_count = revision_count + 1
    trace = [tracer.revision(new_count, max_revisions, feedback.required_revisions or "revision requested")]
    trace.append(tracer.status_change(WorkflowStatus.REVISING))
    return {"revision_count": new_count, "trace": trace, "revision_forced_stop": False}


def finalize(state: WorkflowState) -> Dict[str, Any]:
    """Node: mark the workflow complete once the report is written."""
    trace = [tracer.status_change(WorkflowStatus.COMPLETED)]
    return {"workflow_status": WorkflowStatus.COMPLETED, "trace": trace}


def fail_workflow(reason: str) -> Dict[str, Any]:
    return {
        "workflow_status": WorkflowStatus.FAILED,
        "errors": [{"agent": AGENT_ID, "type": "workflow_terminated", "detail": reason}],
        "trace": [tracer.status_change(WorkflowStatus.FAILED)],
    }
