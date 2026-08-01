"""
Report Writer Agent — Agent 5 (Section 5).

Receives ONLY validated state (approved analysis + evidence store) and
produces the FinalReport. Deliberately has no search-tool permission (see
tool matrix) — it must synthesize, not independently research.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from pydantic import ValidationError

from app.config import settings
from app.graph.state import WorkflowState, WorkflowStatus, CheckpointStatus
from app.observability import tracer
from app.observability.logging_config import get_logger
from app.schemas.reports import FinalReport, Finding, FindingTag
from app.services.llm_client import llm_client

AGENT_ID = "Writer"
logger = get_logger(__name__)


def _extract_json_object(text: str) -> str:
    """Same defensive extraction used in supervisor.py's analyze_request:
    a live LLM response can arrive with stray leading/trailing prose
    despite the system prompt insisting on JSON-only output. Takes the
    substring between the first '{' and the last '}' rather than trusting
    the whole response body to already be clean JSON."""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text

SYSTEM_PROMPT = (
    "You are the Report Writer agent. You receive validated analysis and evidence — "
    "do NOT invent new research. Produce a final report as JSON with keys: title, "
    "executive_summary, research_objective, methodology, findings (list of "
    "{tag: 'evidence'|'analysis'|'recommendation', text}), risks_and_limitations, "
    "recommendation, evidence_references (list of evidence IDs)."
)


def _mock_write(state: WorkflowState) -> str:
    objective = state["research_objective"]
    analysis = state["analysis"]
    evidence = state["evidence"]

    findings = []
    for e in evidence[:6]:
        findings.append({"tag": FindingTag.EVIDENCE.value, "text": e.claim})
    for c in analysis.conclusions:
        findings.append({"tag": FindingTag.ANALYSIS.value, "text": c})

    risks = (
        "; ".join(analysis.known_gaps)
        if analysis.known_gaps
        else "No major evidence gaps identified; confidence is generally Medium-to-High across sources."
    )

    payload = {
        "title": f"{objective.get('objective', 'Research Report')}",
        "executive_summary": (
            f"Based on {len(evidence)} evidence items across {len(analysis.evidence_refs)} cited sources, "
            f"{analysis.conclusions[-1] if analysis.conclusions else 'the options show clear trade-offs.'} "
            "Full trade-offs and caveats are detailed below."
        ),
        "research_objective": objective.get("objective", ""),
        "methodology": (
            "Parallel research tasks gathered corpus-sourced evidence for each option, which the Analyst "
            "compared against the stated evaluation criteria and the Critic reviewed once before finalization."
        ),
        "findings": findings,
        "risks_and_limitations": risks,
        "recommendation": (
            f"{analysis.conclusions[0] if analysis.conclusions else 'See findings above.'} "
            "Recommend validating with a small prototype before committing to a production migration."
        ),
        "evidence_references": analysis.evidence_refs,
    }
    return json.dumps(payload)


def generate_report(state: WorkflowState) -> Dict[str, Any]:
    trace: List[Dict[str, Any]] = [tracer.agent_start(AGENT_ID)]

    # A live LLM call can fail two structurally different ways here, same
    # as analyze_request in supervisor.py: the call itself can error out,
    # or it can return text that parses as JSON but doesn't have the
    # shape FinalReport/Finding expect (e.g. a missing "findings" key, or
    # a finding given as a plain string instead of a {tag, text} object).
    # The previous code only caught (JSONDecodeError, ValidationError) —
    # a missing key or wrong-shaped item raises KeyError/TypeError, which
    # was NOT caught here, so it propagated all the way up through
    # LangGraph's stream() and crashed the whole run thread uncaught
    # (session.status="error" with no clean workflow_status=FAILED, no
    # recorded error entry, no Execution Log entry — exactly what Issue 2
    # described). A longer, more detailed multi-product, multi-criteria
    # comparison report is also more likely to hit this than a short one,
    # both because there's more surface area for a wrong-shaped item and
    # because it's more likely to get truncated at a tight token budget.
    report: Any = None
    last_error_type = "model_api_failure"
    last_error_detail = "unknown error"
    for _ in range(settings.tool_max_retries + 1):
        result = llm_client.complete(
            system=SYSTEM_PROMPT,
            user=json.dumps({"objective": state["research_objective"], "analysis": state["analysis"].model_dump(mode="json")}),
            mock_fn=lambda: _mock_write(state),
            max_tokens=2200,
        )
        if result.error:
            last_error_type, last_error_detail = "model_api_failure", result.error
            continue
        try:
            parsed = json.loads(_extract_json_object(result.text))
            parsed["findings"] = [Finding(**f) for f in parsed["findings"]]
            report = FinalReport(**parsed)
            break
        except (json.JSONDecodeError, ValidationError, TypeError, KeyError) as exc:
            last_error_type, last_error_detail = "invalid_structured_output", str(exc)
            continue

    if report is None:
        trace.append(tracer.error(AGENT_ID, last_error_type, last_error_detail))
        trace.append(tracer.status_change(WorkflowStatus.FAILED))
        logger.error(
            "run %s: generate_report failed after retries — type=%s detail=%s",
            state.get("run_id"), last_error_type, last_error_detail,
        )
        return {
            "errors": [{"agent": AGENT_ID, "type": last_error_type, "detail": last_error_detail}],
            "workflow_status": WorkflowStatus.FAILED,
            "trace": trace,
        }

    trace.append(tracer.agent_end(AGENT_ID))
    trace.append(tracer.status_change(WorkflowStatus.AWAITING_FINAL_APPROVAL))

    return {
        "final_report": report,
        "workflow_status": WorkflowStatus.AWAITING_FINAL_APPROVAL,
        "checkpoint_2_status": CheckpointStatus.WAITING,
        "completed_tasks": ["W1"],
        "trace": trace,
    }
