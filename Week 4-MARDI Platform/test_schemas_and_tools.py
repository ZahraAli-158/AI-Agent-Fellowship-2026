from datetime import date

import pytest

from app.schemas.evidence import ConfidenceLevel, Evidence
from app.schemas.tasks import AgentRole, Priority, Task, TaskStatus
from app.tools.calculator import confidence_distribution, weighted_score
from app.tools.evidence import retrieve_evidence, store_evidence, summarize_evidence_counts
from app.tools.extraction import extract_relevant_excerpt
from app.tools.search import search


def make_evidence(id_="EV-1", rq="R2", confidence=ConfidenceLevel.HIGH, agent="Researcher-LangGraph"):
    return Evidence(
        id=id_,
        claim="Test claim",
        supporting_text="Supporting text",
        source="http://example.com",
        source_title="Example Doc",
        retrieval_date=date.today(),
        research_question=rq,
        confidence=confidence,
        agent_id=agent,
    )


def test_task_is_ready_respects_dependencies():
    t = Task(id="A1", description="x", assigned_agent=AgentRole.ANALYST, dependencies=["R2", "R3"])
    assert not t.is_ready(["R2"])
    assert t.is_ready(["R2", "R3"])
    assert t.is_ready(["R2", "R3", "R4"])  # extra completions are fine


def test_task_default_status_and_priority():
    t = Task(id="R1", description="x", assigned_agent=AgentRole.RESEARCHER)
    assert t.status == TaskStatus.PENDING or t.status == "pending"
    assert t.priority == Priority.MEDIUM or t.priority == "Medium"


def test_store_evidence_deduplicates_by_id():
    existing = [make_evidence("EV-1")]
    incoming = [make_evidence("EV-1"), make_evidence("EV-2")]
    new_items = store_evidence(incoming, target=existing)
    assert [e.id for e in new_items] == ["EV-2"]


def test_retrieve_evidence_filters_by_research_question_and_confidence():
    evidence = [
        make_evidence("EV-1", rq="R2", confidence=ConfidenceLevel.HIGH),
        make_evidence("EV-2", rq="R3", confidence=ConfidenceLevel.LOW),
        make_evidence("EV-3", rq="R2", confidence=ConfidenceLevel.LOW),
    ]
    assert {e.id for e in retrieve_evidence(evidence, research_question="R2")} == {"EV-1", "EV-3"}
    assert {e.id for e in retrieve_evidence(evidence, min_confidence=ConfidenceLevel.HIGH)} == {"EV-1"}


def test_summarize_evidence_counts():
    evidence = [
        make_evidence("EV-1", rq="R2", confidence=ConfidenceLevel.HIGH, agent="Researcher-A"),
        make_evidence("EV-2", rq="R2", confidence=ConfidenceLevel.LOW, agent="Researcher-B"),
    ]
    summary = summarize_evidence_counts(evidence)
    assert summary["by_research_question"]["R2"] == 2
    assert summary["by_agent"]["Researcher-A"] == 1
    assert summary["by_confidence"]["High"] == 1


def test_weighted_score_defaults_to_equal_weight():
    score = weighted_score({"a": 10, "b": 20}, weights={})
    assert score == 15.0


def test_confidence_distribution_percentages():
    dist = confidence_distribution(["High", "High", "Low"])
    assert dist["High"] == pytest.approx(66.7, abs=0.1)
    assert dist["Low"] == pytest.approx(33.3, abs=0.1)


def test_search_returns_structured_empty_result_not_exception():
    result = search(query="totally unrelated nonsense zzz", top_k=3)
    assert result["hit_count"] == 0
    assert result["hits"] == []


def test_search_finds_relevant_docs_for_known_topic():
    result = search(query="LangGraph state management", framework_filter="LangGraph", top_k=2)
    assert result["hit_count"] > 0
    assert all("LangGraph" in d["framework"] for d in result["hits"])


def test_extraction_does_not_split_on_abbreviations():
    doc = {"content": "This uses a reducer, e.g. operator.add, to merge state. It is powerful."}
    excerpt = extract_relevant_excerpt(doc, "reducer merge state", max_sentences=1)
    # The e.g./operator.add sentence must survive as ONE unbroken sentence,
    # not be chopped at the "e.g." or "operator.add" periods.
    assert excerpt.strip() == "This uses a reducer, e.g. operator.add, to merge state."
