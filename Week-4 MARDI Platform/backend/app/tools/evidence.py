"""
Evidence Storage & Retrieval Tools — Requirement 6 (Section 14).

A minimal in-memory evidence store. In this design, the *source of truth*
for evidence within a single workflow run is the LangGraph WorkflowState
(`state["evidence"]`) — these functions exist as the explicit "Evidence
Storage Tool" / "Evidence Retrieval Tool" the assignment calls for, and are
what the Researcher/Analyst agents call rather than mutating state directly.
A production version would back this with a real database (see
app/config.py for where a DSN would be added).
"""
from __future__ import annotations

from typing import Dict, List

from app.schemas.evidence import ConfidenceLevel, Evidence


def store_evidence(evidence_list: List[Evidence], target: List[Evidence]) -> List[Evidence]:
    """Appends new evidence to a target list, skipping duplicate IDs.
    Returns the list of newly stored (non-duplicate) items — this is what
    gets merged into WorkflowState.evidence by LangGraph's reducer.
    """
    existing_ids = {e.id for e in target}
    new_items = [e for e in evidence_list if e.id not in existing_ids]
    return new_items


def retrieve_evidence(
    evidence: List[Evidence],
    research_question: str | None = None,
    min_confidence: ConfidenceLevel | None = None,
) -> List[Evidence]:
    """Filters the evidence store for what a downstream agent needs —
    e.g. the Analyst only asks for evidence tied to specific research
    questions rather than receiving the entire store unfiltered."""
    results = evidence
    if research_question:
        results = [e for e in results if e.research_question == research_question]
    if min_confidence:
        order = {ConfidenceLevel.LOW: 0, ConfidenceLevel.MEDIUM: 1, ConfidenceLevel.HIGH: 2}
        threshold = order[min_confidence]
        results = [e for e in results if order[ConfidenceLevel(e.confidence)] >= threshold]
    return results


def summarize_evidence_counts(evidence: List[Evidence]) -> Dict[str, Dict[str, int]]:
    """Aggregates evidence for dashboard/report use: by research question,
    by agent, and by confidence level — without dumping full evidence text."""
    by_rq: Dict[str, int] = {}
    by_agent: Dict[str, int] = {}
    by_confidence: Dict[str, int] = {}
    for e in evidence:
        by_rq[e.research_question] = by_rq.get(e.research_question, 0) + 1
        by_agent[e.agent_id] = by_agent.get(e.agent_id, 0) + 1
        conf = e.confidence if isinstance(e.confidence, str) else e.confidence.value
        by_confidence[conf] = by_confidence.get(conf, 0) + 1
    return {"by_research_question": by_rq, "by_agent": by_agent, "by_confidence": by_confidence}
