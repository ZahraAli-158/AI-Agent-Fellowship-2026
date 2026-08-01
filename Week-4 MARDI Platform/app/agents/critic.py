"""
Critic / Reviewer Agent — Agent 4 (Section 5).

Evaluates the Analyst's output against six minimum review criteria
(Requirement 10): evidence coverage, logical consistency, completeness,
unsupported claims, contradictions, relevance. It never rewrites the
analysis itself — it only produces the Analyst -> Critic -> Supervisor
handoff contract (CriticFeedback) from Requirement 9.

The revision loop itself (cap at max_revisions, forced termination) is
enforced in app/graph/routing.py, NOT here — the Critic can request as
many revisions as it wants; only the graph's routing decides when to stop
listening to it.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from pydantic import ValidationError

from app.graph.state import WorkflowState, WorkflowStatus
from app.observability import tracer
from app.observability.logging_config import get_logger
from app.schemas.reports import AnalysisOutput, CriticDecision, CriticFeedback
from app.services.llm_client import llm_client

AGENT_ID = "Critic"
logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are the Critic agent. Evaluate the Analyst's output against these criteria: "
    "evidence coverage, logical consistency, completeness, unsupported claims, "
    "contradictions, relevance. Do NOT rewrite the analysis. Respond as JSON with keys: "
    "decision ('approved' or 'revision_requested'), problems_found (list), "
    "missing_evidence (list), required_revisions (string or null), criteria_scores (object)."
)


def _mock_review(analysis: AnalysisOutput, revision_count: int) -> str:
    criteria_scores = {
        "evidence_coverage": "pass" if analysis.evidence_refs else "fail",
        "logical_consistency": "pass",
        "completeness": "pass" if len(analysis.conclusions) >= 2 else "fail",
        "unsupported_claims": "fail" if not analysis.known_gaps and revision_count == 0 else "pass",
        "contradictions": "pass",
        "relevance": "pass",
    }

    # First pass: if the analysis itself flagged a confidence gap, ask for one
    # concrete revision. On any subsequent pass, approve — this both
    # demonstrates the quality-control loop AND its guaranteed termination.
    if revision_count == 0 and analysis.known_gaps:
        payload = {
            "decision": CriticDecision.REVISION_REQUESTED.value,
            "problems_found": [
                "The weakest-evidenced comparison criterion is not explicitly flagged as low-confidence in the conclusions."
            ],
            "missing_evidence": analysis.known_gaps,
            "required_revisions": "Explicitly label the low-confidence criterion as an open evidence gap rather than an implicit conclusion.",
            "criteria_scores": criteria_scores,
        }
    else:
        criteria_scores["unsupported_claims"] = "pass"
        payload = {
            "decision": CriticDecision.APPROVED.value,
            "problems_found": [],
            "missing_evidence": [],
            "required_revisions": None,
            "criteria_scores": criteria_scores,
        }
    return json.dumps(payload)


def review(state: WorkflowState) -> Dict[str, Any]:
    trace: List[Dict[str, Any]] = [tracer.agent_start(AGENT_ID)]
    analysis: AnalysisOutput = state["analysis"]
    revision_count = state.get("revision_count", 0)

    result = llm_client.complete(
        system=SYSTEM_PROMPT,
        user=analysis.model_dump_json(),
        mock_fn=lambda: _mock_review(analysis, revision_count),
    )
    if result.error:
        trace.append(tracer.error(AGENT_ID, "model_api_failure", result.error))
        trace.append(tracer.status_change(WorkflowStatus.FAILED))
        logger.error("run %s: model_api_failure — %s", state.get("run_id"), result.error)
        return {
            "errors": [{"agent": AGENT_ID, "type": "model_api_failure", "detail": result.error}],
            "workflow_status": WorkflowStatus.FAILED,
            "trace": trace,
        }

    try:
        parsed = json.loads(result.text)
        feedback = CriticFeedback(**parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        trace.append(tracer.error(AGENT_ID, "invalid_structured_output", str(exc)))
        trace.append(tracer.status_change(WorkflowStatus.FAILED))
        logger.error("run %s: invalid_structured_output — %s", state.get("run_id"), exc)
        return {
            "errors": [{"agent": AGENT_ID, "type": "invalid_structured_output", "detail": str(exc)}],
            "workflow_status": WorkflowStatus.FAILED,
            "trace": trace,
        }

    trace.append(tracer.agent_end(AGENT_ID))
    trace.append(tracer.handoff(AGENT_ID, "Supervisor", f"decision={feedback.decision}"))
    new_status = (
        WorkflowStatus.REVISING if feedback.decision == CriticDecision.REVISION_REQUESTED.value else WorkflowStatus.WRITING_REPORT
    )
    trace.append(tracer.status_change(new_status))

    return {"critic_feedback": feedback, "workflow_status": new_status, "completed_tasks": ["C1"], "trace": trace}
