"""
Additional automated tests closing the gaps in Section 33's required
coverage list that test_graph.py and test_schemas_and_tools.py don't hit
directly: Request Parsing, Structured Task Planning, State Updates, Tool
Permissions, Agent Handoffs (schema contracts), Critic Approval/Rejection
(the actual node, not just routing), Invalid Output Handling, Tool
Failure, Human Approval, and Report Generation.

All LLM calls are mocked via each agent's `mock_fn` injection point — no
network access or API key is required to run this file.
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from app.agents import analyst, critic, researcher, supervisor, writer
from app.graph import human
from app.graph.state import WorkflowStatus, new_state
from app.schemas.evidence import ConfidenceLevel, Evidence
from app.schemas.reports import AnalysisOutput, CriticDecision, CriticFeedback, FinalReport
from app.schemas.tasks import AgentRole, Task
from app.services.llm_client import LLMClient, LLMResult


# --------------------------------------------------------------------------
# Request Parsing (Requirement 1)
# --------------------------------------------------------------------------

def test_request_parsing_extracts_structured_objective(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    state = new_state("t1", "Compare three cloud platforms for deploying an AI SaaS application.")
    result = supervisor.analyze_request(state)
    obj = result["research_objective"]
    assert obj["objective"]
    assert len(obj["sub_questions"]) >= 3
    assert isinstance(obj["evaluation_criteria"], list)
    assert result["needs_clarification"] is False


def test_request_parsing_flags_ambiguous_request_for_clarification():
    state = new_state("t2", "best framework")
    result = supervisor.analyze_request(state)
    assert result["needs_clarification"] is True
    assert len(result["clarification_questions"]) > 0


# --------------------------------------------------------------------------
# Structured Task Planning (Requirement 3)
# --------------------------------------------------------------------------

def test_structured_task_planning_generates_dependent_tasks():
    state = new_state("t3", "Compare three cloud platforms for deploying an AI SaaS application.")
    state.update(supervisor.analyze_request(state))
    result = supervisor.create_plan(state)
    plan = result["task_plan"]
    ids = [t.id for t in plan]
    assert ids == ["R1", "R2", "R3", "R4", "A1", "C1", "W1"]
    a1 = next(t for t in plan if t.id == "A1")
    assert set(a1.dependencies) == {"R2", "R3", "R4"}


def test_structured_task_planning_depends_on_request_content():
    """Different requests must yield different research targets — plan is
    not a hard-coded fixed sequence (Requirement 3)."""
    frameworks_state = new_state("t4a", "Research the current open-source agent frameworks.")
    frameworks_state.update(supervisor.analyze_request(frameworks_state))
    frameworks_plan = supervisor.create_plan(frameworks_state)["task_plan"]

    cloud_state = new_state("t4b", "Compare three cloud platforms for deploying an AI SaaS application.")
    cloud_state.update(supervisor.analyze_request(cloud_state))
    cloud_plan = supervisor.create_plan(cloud_state)["task_plan"]

    frameworks_targets = {t.parameters.get("target") for t in frameworks_plan if t.parameters.get("target")}
    cloud_targets = {t.parameters.get("target") for t in cloud_plan if t.parameters.get("target")}
    assert frameworks_targets != cloud_targets


# --------------------------------------------------------------------------
# State Updates (Requirement 8)
# --------------------------------------------------------------------------

def test_new_state_initializes_all_required_fields():
    state = new_state("t5", "some request")
    for field in ["user_request", "clarifications", "research_objective", "task_plan",
                  "current_tasks", "completed_tasks", "evidence", "analysis",
                  "critic_feedback", "revision_count", "final_report", "errors", "workflow_status"]:
        assert field in state
    assert state["workflow_status"] == WorkflowStatus.PENDING
    assert state["evidence"] == []
    assert state["revision_count"] == 0


def test_state_reducer_merges_parallel_evidence_writes():
    """Simulates what LangGraph's operator.add reducer does when two
    parallel researcher branches each return an `evidence` list in the same
    superstep — the merged result must contain both, not overwrite."""
    import operator
    branch_a = [Evidence(id="EV-A", claim="x", supporting_text="x", source="s", source_title="s",
                          retrieval_date=date.today(), research_question="R2", confidence=ConfidenceLevel.HIGH, agent_id="Researcher-A")]
    branch_b = [Evidence(id="EV-B", claim="y", supporting_text="y", source="s", source_title="s",
                          retrieval_date=date.today(), research_question="R3", confidence=ConfidenceLevel.HIGH, agent_id="Researcher-B")]
    merged = operator.add(branch_a, branch_b)
    assert {e.id for e in merged} == {"EV-A", "EV-B"}


# --------------------------------------------------------------------------
# Tool Permissions (Requirement 5)
# --------------------------------------------------------------------------

def test_tool_permission_boundaries_match_documented_matrix():
    """Structural check: each agent module only imports the tools it is
    documented to be allowed (docs/tool_permission_boundaries.md)."""
    import inspect

    supervisor_src = inspect.getsource(supervisor)
    researcher_src = inspect.getsource(researcher)
    analyst_src = inspect.getsource(analyst)
    critic_src = inspect.getsource(critic)
    writer_src = inspect.getsource(writer)

    # Supervisor: no search tool access — it must never research itself.
    assert "from app.tools.search import" not in supervisor_src
    # Researcher: has search tool access.
    assert "from app.tools.search import" in researcher_src
    # Analyst: no search access, but does have the calculator tool available.
    assert "from app.tools.search import" not in analyst_src
    # Critic: no search, no calculator — pure evaluation of the Analyst's output.
    assert "from app.tools.search import" not in critic_src
    assert "from app.tools.calculator import" not in critic_src
    # Writer: no search access — must synthesize only, never research.
    assert "from app.tools.search import" not in writer_src


# --------------------------------------------------------------------------
# Agent Handoffs (Requirement 9) — schema contract validation
# --------------------------------------------------------------------------

def test_researcher_to_analyst_handoff_schema_has_required_fields():
    e = Evidence(id="EV-1", claim="c", supporting_text="s", source="src", source_title="t",
                 retrieval_date=date.today(), research_question="R2", confidence=ConfidenceLevel.HIGH, agent_id="Researcher-X")
    dumped = e.model_dump()
    for field in ["research_question", "claim", "confidence", "agent_id", "id"]:
        assert field in dumped


def test_analyst_to_critic_handoff_schema_has_required_fields():
    a = AnalysisOutput(comparison_framework="f", conclusions=["c1"], evidence_refs=["EV-1"], assumptions=["a1"], known_gaps=[])
    dumped = a.model_dump()
    for field in ["comparison_framework", "conclusions", "evidence_refs", "assumptions"]:
        assert field in dumped


def test_critic_to_supervisor_handoff_schema_has_required_fields():
    f = CriticFeedback(decision=CriticDecision.REVISION_REQUESTED, problems_found=["p1"], missing_evidence=["m1"], required_revisions="fix x")
    dumped = f.model_dump()
    for field in ["decision", "problems_found", "missing_evidence", "required_revisions"]:
        assert field in dumped


# --------------------------------------------------------------------------
# Critic Approval / Rejection (the actual node)
# --------------------------------------------------------------------------

def _sample_analysis(known_gaps=None):
    return AnalysisOutput(
        comparison_framework="weighted", conclusions=["A is better", "B is faster"],
        evidence_refs=["EV-1", "EV-2"], assumptions=["docs are representative"],
        known_gaps=known_gaps or [],
    )


def test_critic_requests_revision_when_analysis_has_known_gaps():
    state = new_state("t6", "x")
    state["analysis"] = _sample_analysis(known_gaps=["reliability data is thin"])
    state["revision_count"] = 0
    result = critic.review(state)
    assert result["critic_feedback"].decision == CriticDecision.REVISION_REQUESTED.value
    assert result["workflow_status"] == WorkflowStatus.REVISING


def test_critic_approves_when_no_gaps_or_already_revised_once():
    state = new_state("t7", "x")
    state["analysis"] = _sample_analysis(known_gaps=[])
    state["revision_count"] = 0
    result = critic.review(state)
    assert result["critic_feedback"].decision == CriticDecision.APPROVED.value
    assert result["workflow_status"] == WorkflowStatus.WRITING_REPORT


# --------------------------------------------------------------------------
# Invalid Output Handling (Requirement 14)
# --------------------------------------------------------------------------

def test_analyze_request_handles_invalid_json_from_llm(monkeypatch):
    def broken_complete(self, system, user, mock_fn=None, max_tokens=1200):
        return LLMResult(text="not valid json {{{", mode="mock")

    monkeypatch.setattr(LLMClient, "complete", broken_complete)
    state = new_state("t8", "Compare three cloud platforms.")
    result = supervisor.analyze_request(state)
    assert result["workflow_status"] == WorkflowStatus.FAILED
    assert result["errors"][0]["type"] == "invalid_structured_output"


# --------------------------------------------------------------------------
# Tool Failure (Requirement 14) — search failure / empty results / retry
# --------------------------------------------------------------------------

def test_researcher_logs_empty_research_results_without_crashing():
    task = Task(id="R2", description="Research NonexistentFrameworkXYZ", assigned_agent=AgentRole.RESEARCHER,
                dependencies=["R1"], parameters={"target": "NonexistentFrameworkXYZ123", "topic": "nothing"})
    result = researcher.research_task({"task": task})
    # Should degrade gracefully: task marked complete, an error logged, no evidence, no exception.
    assert result["completed_tasks"] == ["R2"]
    assert result["errors"][0]["type"] == "empty_research_results"
    assert "evidence" not in result or result.get("evidence", []) == []


# --------------------------------------------------------------------------
# Human Approval (Requirement 12)
# --------------------------------------------------------------------------

def test_human_checkpoint_plan_approval_records_decision():
    state = new_state("t9", "x")
    state["research_objective"] = {"objective": "test objective"}
    state["task_plan"] = [Task(id="R1", description="d", assigned_agent=AgentRole.SUPERVISOR)]
    result = human.checkpoint_plan_approval(state, lambda name, payload: {"decision": "approved"})
    assert result["checkpoint_1_status"] == "approved"
    assert result["workflow_status"] == WorkflowStatus.RESEARCHING


def test_human_checkpoint_plan_rejection_fails_workflow():
    state = new_state("t10", "x")
    state["research_objective"] = {"objective": "test objective"}
    state["task_plan"] = []
    result = human.checkpoint_plan_approval(state, lambda name, payload: {"decision": "rejected"})
    assert result["checkpoint_1_status"] == "rejected"
    assert result["workflow_status"] == WorkflowStatus.FAILED


def test_human_clarification_checkpoint_records_answers():
    state = new_state("t11", "best framework")
    state["clarification_questions"] = ["What use case?"]
    result = human.request_clarification(state, lambda name, payload: {"answers": ["a web scraper"]})
    assert result["clarifications"] == ["a web scraper"]
    assert result["needs_clarification"] is False


# --------------------------------------------------------------------------
# Report Generation (Requirement 17)
# --------------------------------------------------------------------------

def test_writer_generates_report_with_all_required_sections():
    state = new_state("t12", "Research agent frameworks.")
    state["research_objective"] = {"objective": "Recommend a framework", "_topic": "agent_frameworks"}
    state["analysis"] = _sample_analysis()
    state["evidence"] = [
        Evidence(id="EV-1", claim="LangGraph is explicit", supporting_text="s", source="src", source_title="t",
                 retrieval_date=date.today(), research_question="R2", confidence=ConfidenceLevel.HIGH, agent_id="Researcher-LangGraph"),
    ]
    result = writer.generate_report(state)
    report: FinalReport = result["final_report"]
    md = report.to_markdown()
    for heading in ["Executive Summary", "Research Objective", "Methodology", "Key Findings",
                     "Risks and Limitations", "Recommendation", "Evidence and References"]:
        assert heading in md
    assert result["completed_tasks"] == ["W1"]
