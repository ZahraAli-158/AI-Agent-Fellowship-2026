"""
Analyst Agent — Agent 3 (Section 5).

Consumes the Evidence store (filtered/retrieved, not the full chat history)
and produces a structured AnalysisOutput — the Researcher -> Analyst ->
Critic handoff contract from Requirement 9. Works primarily from retrieved
evidence; any assumption it makes is explicitly labeled as one, never
presented as a fact.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from pydantic import ValidationError

from app.graph.state import WorkflowState, WorkflowStatus
from app.observability import tracer
from app.observability.logging_config import get_logger
from app.schemas.reports import AnalysisOutput
from app.services.llm_client import llm_client
from app.tools.calculator import confidence_distribution
from app.tools.evidence import retrieve_evidence

AGENT_ID = "Analyst"
logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are the Analyst agent. You work ONLY from the evidence provided to you — "
    "never invent facts not present in the evidence. Compare the alternatives, "
    "identify trade-offs, and respond as JSON with keys: comparison_framework, "
    "conclusions (list), evidence_refs (list of evidence IDs used), assumptions (list), "
    "known_gaps (list). IMPORTANT: comparison_framework MUST be a single plain string "
    "(e.g. \"Weighted comparison across cost, reliability, and support\"), never a nested "
    "object — do not use sub-fields like 'dimensions' for it."
)


def _coerce_analysis_fields(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Defensive normalization for live-LLM output that doesn't strictly follow
    the requested flat schema (observed in practice: some models return
    comparison_framework as a nested object with a 'dimensions' list instead
    of the requested plain string). Converts a non-string comparison_framework
    into a readable string instead of letting Pydantic reject the whole
    analysis outright — the goal is graceful degradation, not silent data loss."""
    cf = parsed.get("comparison_framework")
    if isinstance(cf, dict):
        dims = cf.get("dimensions") or cf.get("criteria") or list(cf.values())
        if isinstance(dims, list):
            parsed["comparison_framework"] = "Comparison across: " + ", ".join(str(d) for d in dims)
        else:
            parsed["comparison_framework"] = json.dumps(cf)
    elif not isinstance(cf, str):
        parsed["comparison_framework"] = str(cf)
    return parsed


def _mock_analyze(evidence, criteria: List[str], prior_feedback) -> str:
    by_target: Dict[str, List[Any]] = {}
    for e in evidence:
        target = e.agent_id.split("-", 1)[-1] if "-" in e.agent_id else e.agent_id
        by_target.setdefault(target, []).append(e)

    conclusions = []
    for target, items in by_target.items():
        top_claim = items[0].claim
        conclusions.append(f"{target}: {top_claim}")

    if len(by_target) >= 2:
        conclusions.append(
            "Trade-off: options with simpler abstractions (fewer moving parts) tend to "
            "get to a first prototype faster, while options with explicit state/graph "
            "control scale better as workflow complexity grows."
        )

    known_gaps = []
    dist = confidence_distribution([e.confidence for e in evidence])
    if dist.get("Low", 0) > 0:
        known_gaps.append("Reliability/production-readiness evidence is thin (Low confidence) for at least one option.")

    if prior_feedback:
        conclusions.append(f"Revision note: addressed — {prior_feedback.required_revisions}")

    payload = {
        "comparison_framework": f"Weighted comparison across: {', '.join(criteria)}",
        "conclusions": conclusions,
        "evidence_refs": [e.id for e in evidence],
        "assumptions": [
            "Assumed each source's documentation reflects typical real-world usage, not just the ideal case."
        ],
        "known_gaps": known_gaps,
    }
    return json.dumps(payload)


def analyze(state: WorkflowState) -> Dict[str, Any]:
    trace: List[Dict[str, Any]] = [tracer.agent_start(AGENT_ID)]

    evidence = retrieve_evidence(state["evidence"])
    criteria = state["research_objective"].get("evaluation_criteria", [])
    prior_feedback = state.get("critic_feedback")

    if not evidence:
        trace.append(tracer.error(AGENT_ID, "missing_evidence", "No evidence available to analyze"))
        trace.append(tracer.status_change(WorkflowStatus.FAILED))
        logger.error("run %s: missing_evidence — empty evidence store, cannot analyze", state.get("run_id"))
        return {
            "errors": [{"agent": AGENT_ID, "type": "missing_evidence", "detail": "empty evidence store"}],
            "workflow_status": WorkflowStatus.FAILED,
            "trace": trace,
        }

    result = llm_client.complete(
        system=SYSTEM_PROMPT,
        user=json.dumps({"evidence": [e.model_dump(mode="json") for e in evidence], "criteria": criteria}),
        mock_fn=lambda: _mock_analyze(evidence, criteria, prior_feedback),
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
        parsed = _coerce_analysis_fields(parsed)
        analysis = AnalysisOutput(**parsed)
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
    trace.append(tracer.handoff(AGENT_ID, "Critic", f"{len(analysis.conclusions)} conclusions, {len(analysis.evidence_refs)} evidence refs"))
    trace.append(tracer.status_change(WorkflowStatus.REVIEWING))

    return {"analysis": analysis, "workflow_status": WorkflowStatus.REVIEWING, "completed_tasks": ["A1"], "trace": trace}
