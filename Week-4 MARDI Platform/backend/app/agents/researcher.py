"""
Research Agent — Agent 2 (Section 5).

Runs once per research task (R2, R3, R4, ...), dispatched in PARALLEL via
LangGraph's Send API (Requirement 11). Each invocation is independent: it
searches the local corpus, extracts relevant excerpts, and returns
structured Evidence. Only this agent may call the search tool.

Failure handling implemented here (Requirement 14):
  - Search Failure / Empty Research Results -> retry once with a broader
    query, then log a structured gap if still empty (never crashes).
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from app.config import settings
from app.observability import tracer
from app.observability.logging_config import get_logger
from app.schemas.evidence import ConfidenceLevel, Evidence, EvidenceType
from app.tools.evidence import store_evidence
from app.tools.extraction import extract_relevant_excerpt
from app.tools.search import search

logger = get_logger(__name__)

AGENT_ID_PREFIX = "Researcher"


def _confidence_for(doc: Dict[str, Any], rank: int) -> ConfidenceLevel:
    title = doc.get("title", "").lower()
    if "community" in title or "informal" in title or "aggregated" in title:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.HIGH if rank == 0 else ConfidenceLevel.MEDIUM


def _evidence_type_for(doc: Dict[str, Any]) -> EvidenceType:
    title = doc.get("title", "").lower()
    if "community" in title or "aggregated" in title:
        return EvidenceType.CLAIM
    return EvidenceType.FACT


def research_task(input: Dict[str, Any]) -> Dict[str, Any]:
    """Node invoked once per parallel research task via Send({'task': task, ...})."""
    task = input["task"]
    target = task.parameters.get("target", task.description)
    topic = task.parameters.get("topic", "general")
    agent_id = f"{AGENT_ID_PREFIX}-{target}"

    trace: List[Dict[str, Any]] = [tracer.agent_start(agent_id)]

    result = search(query=f"{target} {topic}", framework_filter=target, top_k=2)
    trace.append(tracer.tool_call(agent_id, "search_tool", result["hit_count"] > 0, f"query='{target} {topic}'"))

    retries = 0
    while result["hit_count"] == 0 and retries < settings.tool_max_retries:
        retries += 1
        result = search(query=target, top_k=2)  # broaden the query and retry
        trace.append(tracer.tool_call(agent_id, "search_tool", result["hit_count"] > 0, f"retry #{retries}, query='{target}'"))

    if result["hit_count"] == 0:
        trace.append(tracer.error(agent_id, "empty_research_results", f"No corpus hits for '{target}'"))
        trace.append(tracer.agent_end(agent_id))
        logger.warning("task %s: empty_research_results — no corpus hits for %r", task.id, target)
        return {
            "completed_tasks": [task.id],
            "errors": [{"agent": agent_id, "type": "empty_research_results", "detail": target}],
            "trace": trace,
        }

    new_evidence: List[Evidence] = []
    for rank, doc in enumerate(result["hits"]):
        excerpt = extract_relevant_excerpt(doc, task.description)
        claim_text = excerpt if excerpt else f"{target}: see source for details."
        if len(claim_text) > 180:
            claim_text = claim_text[:180].rsplit(" ", 1)[0] + "…"
        new_evidence.append(
            Evidence(
                id=f"EV-{task.id}-{rank + 1}",
                claim=claim_text,
                supporting_text=excerpt or doc["content"][:200],
                source=doc["source"],
                source_title=doc["title"],
                retrieval_date=date.today(),
                research_question=task.id,
                confidence=_confidence_for(doc, rank),
                agent_id=agent_id,
                evidence_type=_evidence_type_for(doc),
            )
        )

    if task.parameters.get("also_check_reliability"):
        reliability_result = search(query="production readiness reliability benchmark", top_k=1)
        trace.append(tracer.tool_call(agent_id, "search_tool", reliability_result["hit_count"] > 0, "cross-cutting reliability check"))
        for rank, doc in enumerate(reliability_result["hits"]):
            excerpt = extract_relevant_excerpt(doc, "production readiness reliability")
            claim_text = excerpt or doc["content"][:200]
            if len(claim_text) > 180:
                claim_text = claim_text[:180].rsplit(" ", 1)[0] + "…"
            new_evidence.append(
                Evidence(
                    id=f"EV-{task.id}-REL-{rank + 1}",
                    claim=claim_text,
                    supporting_text=excerpt or doc["content"][:200],
                    source=doc["source"],
                    source_title=doc["title"],
                    retrieval_date=date.today(),
                    research_question=task.id,
                    confidence=_confidence_for(doc, rank + 1),  # never rank 0 -> never forced High
                    agent_id=agent_id,
                    evidence_type=_evidence_type_for(doc),
                )
            )

    stored = store_evidence(new_evidence, target=[])
    trace.append(tracer.tool_call(agent_id, "evidence_storage_tool", True, f"stored {len(stored)} items"))
    trace.append(tracer.agent_end(agent_id))
    trace.append(tracer.handoff(agent_id, "Analyst", f"{len(stored)} evidence items for {task.id}"))

    return {
        "evidence": stored,
        "completed_tasks": [task.id],
        "trace": trace,
    }
