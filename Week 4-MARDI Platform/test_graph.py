"""
Graph-level tests. These exercise routing.py directly (fast, no LLM calls
needed since these are pure functions of state) plus one full end-to-end
mock-mode workflow run to prove the whole graph wires together correctly.
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("LLM_MODE", "mock")

from langgraph.graph import END
from langgraph.types import Send

from unittest.mock import patch

from app.agents import supervisor
from app.graph import routing
from app.graph.state import WorkflowStatus, new_state
from app.schemas.reports import AnalysisOutput, CriticDecision, CriticFeedback
from app.schemas.tasks import AgentRole, Priority, Task, TaskStatus
from app.services.llm_client import LLMResult


def test_route_after_request_analysis_goes_to_clarify_when_needed():
    state = new_state("r1", "best framework")
    state["needs_clarification"] = True
    assert routing.route_after_request_analysis(state) == "clarify"


def test_route_after_request_analysis_skips_clarify_when_not_needed():
    state = new_state("r1", "Compare LangGraph and CrewAI for a small team")
    state["needs_clarification"] = False
    assert routing.route_after_request_analysis(state) == "create_plan"


def test_route_after_request_analysis_short_circuits_on_failure():
    state = new_state("r1", "x")
    state["workflow_status"] = WorkflowStatus.FAILED
    assert routing.route_after_request_analysis(state) == END


def test_dispatch_research_sends_only_ready_tasks():
    state = new_state("r1", "x")
    state["task_plan"] = [
        Task(id="R1", description="scope", assigned_agent=AgentRole.SUPERVISOR, status=TaskStatus.COMPLETED),
        Task(id="R2", description="research A", assigned_agent=AgentRole.RESEARCHER, dependencies=["R1"]),
        Task(id="R3", description="research B", assigned_agent=AgentRole.RESEARCHER, dependencies=["R1"]),
        Task(id="A1", description="analyze", assigned_agent=AgentRole.ANALYST, dependencies=["R2", "R3"]),
    ]
    state["completed_tasks"] = ["R1"]

    sends = routing.dispatch_research(state)
    assert isinstance(sends, list)
    assert len(sends) == 2
    assert all(isinstance(s, Send) and s.node == "researcher" for s in sends)


def test_dispatch_research_does_not_dispatch_already_completed_tasks():
    state = new_state("r1", "x")
    state["task_plan"] = [
        Task(id="R1", description="scope", assigned_agent=AgentRole.SUPERVISOR, status=TaskStatus.COMPLETED),
        Task(id="R2", description="research A", assigned_agent=AgentRole.RESEARCHER, dependencies=["R1"]),
    ]
    state["completed_tasks"] = ["R1", "R2"]
    sends = routing.dispatch_research(state)
    assert sends == "analyst"


def _feedback(decision: CriticDecision) -> CriticFeedback:
    return CriticFeedback(decision=decision, problems_found=[], missing_evidence=[], required_revisions=None)


def test_revision_loop_terminates_when_critic_keeps_rejecting():
    """Requirement 10: the loop must terminate even if the Critic never approves.
    routing.route_after_critic_decision now trusts the explicit
    `revision_forced_stop` flag set by supervisor.decide_after_critic,
    rather than re-deriving the cap from revision_count — set here exactly
    as decide_after_critic would."""
    state = new_state("r1", "x", max_revisions=2)
    state["critic_feedback"] = _feedback(CriticDecision.REVISION_REQUESTED)

    # Cycle 1: under the cap -> decide_after_critic would increment and NOT force-stop.
    state["revision_count"] = 1
    state["revision_forced_stop"] = False
    assert routing.route_after_critic_decision(state) == "analyst"

    # Cycle 2: at the cap -> decide_after_critic forces termination.
    state["revision_count"] = 2
    state["revision_forced_stop"] = True
    assert routing.route_after_critic_decision(state) == "writer"


def test_revision_limit_of_one_actually_allows_one_real_revision():
    """Regression test for a real off-by-one bug found via Experiment 5
    (Section 30): max_revisions=1 must let the Analyst actually run ONE
    revised pass, not silently behave like max_revisions=0. This exercises
    the full decide_after_critic -> route_after_critic_decision pipeline
    together, since the bug was in how they interacted, not either
    function in isolation."""
    from app.agents import supervisor as supervisor_agent

    state = new_state("r2", "x", max_revisions=1)
    state["critic_feedback"] = _feedback(CriticDecision.REVISION_REQUESTED)
    state["revision_count"] = 0

    decision_update = supervisor_agent.decide_after_critic(state)
    state.update(decision_update)
    assert state["revision_count"] == 1
    assert state["revision_forced_stop"] is False

    # The Analyst MUST get to run this cycle — this is exactly the case
    # that was broken (routing went straight to "writer" here before the fix).
    assert routing.route_after_critic_decision(state) == "analyst"


def test_revision_loop_exits_immediately_on_approval():
    state = new_state("r1", "x", max_revisions=2)
    state["critic_feedback"] = _feedback(CriticDecision.APPROVED)
    state["revision_count"] = 0
    assert routing.route_after_critic_decision(state) == "writer"


def test_route_after_analysis_guards_missing_evidence_failure():
    state = new_state("r1", "x")
    state["analysis"] = None
    assert routing.route_after_analysis(state) == END

    state["analysis"] = AnalysisOutput(
        comparison_framework="x", conclusions=["a"], evidence_refs=["EV-1"], assumptions=[], known_gaps=[]
    )
    assert routing.route_after_analysis(state) == "critic"


def test_full_workflow_end_to_end_in_mock_mode():
    """Smoke test: the whole graph runs to completion without a real API key."""
    from app.graph.workflow import run_workflow

    final_state = run_workflow(
        user_request="Research the current open-source agent frameworks and recommend one for a small engineering team.",
        run_id="TEST-RUN-1",
        max_revisions=2,
    )
    assert final_state["workflow_status"] == WorkflowStatus.COMPLETED
    assert final_state["final_report"] is not None
    assert len(final_state["evidence"]) > 0
    assert final_state["revision_count"] <= 2
    assert final_state["checkpoint_1_status"] == "approved"
    assert final_state["checkpoint_2_status"] == "approved"


def test_analyze_request_recovers_from_one_truncated_live_response():
    """Regression test for the 'workflow fails before task planning' bug: a
    live LLM call that returns truncated/malformed JSON on its first
    attempt (e.g. cut off mid-array on a detailed multi-criteria request)
    must not permanently fail the workflow if a retry succeeds."""
    truncated = '{"objective": "Recommend a cloud platform.", "sub_questions": ["What are the opti'
    valid = (
        '{"objective": "Recommend a cloud platform.", "sub_questions": ["q1"], '
        '"evaluation_criteria": ["c1"], "constraints": [], "missing_information": [], '
        '"needs_clarification": false, "clarification_questions": []}'
    )
    state = new_state("TEST-RETRY", "Recommend the best cloud platform for a healthcare AI SaaS.")
    with patch(
        "app.services.llm_client.llm_client.complete",
        side_effect=[LLMResult(text=truncated, mode="live"), LLMResult(text=valid, mode="live")],
    ):
        result = supervisor.analyze_request(state)
    assert result["workflow_status"] != WorkflowStatus.FAILED
    assert result["research_objective"]["objective"] == "Recommend a cloud platform."
    assert result.get("errors", []) == []


def test_analyze_request_still_fails_cleanly_after_exhausting_retries():
    """If every attempt returns unparsable JSON, the workflow must still
    fail cleanly (not hang, not crash) with a recorded error — retries add
    resilience but must not remove the failure path entirely."""
    truncated = '{"objective": "Recommend a cloud platform.", "sub_questions": ["What are the opti'
    state = new_state("TEST-RETRY-FAIL", "Recommend the best cloud platform for a healthcare AI SaaS.")
    with patch(
        "app.services.llm_client.llm_client.complete",
        return_value=LLMResult(text=truncated, mode="live"),
    ):
        result = supervisor.analyze_request(state)
    assert result["workflow_status"] == WorkflowStatus.FAILED
    assert result["errors"][0]["type"] == "invalid_structured_output"


def test_request_changes_increments_revision_count():
    """Regression test: clicking 'Request Changes' at checkpoint 2 must
    increment revision_count, exactly like the Critic's automatic
    rejection loop does via decide_after_critic. Previously this path
    updated workflow_status but silently left revision_count untouched."""
    from app.graph import human
    from app.schemas.reports import FinalReport, Finding, FindingTag

    state = new_state("CP2-TEST", "test request")
    state["final_report"] = FinalReport(
        title="T", executive_summary="x", research_objective="x", methodology="x",
        findings=[Finding(tag=FindingTag.EVIDENCE, text="x")], risks_and_limitations="x",
        recommendation="x", evidence_references=[],
    )
    state["max_revisions"] = 2
    state["revision_count"] = 0

    result = human.checkpoint_final_review(state, lambda name, payload: {"decision": "request_changes"})
    assert result["revision_count"] == 1
    assert result["workflow_status"] == WorkflowStatus.REVISING


def test_request_changes_respects_revision_cap():
    """Regression test: once revision_count reaches max_revisions, further
    'Request Changes' clicks must not increment past the cap, and routing
    must send the workflow to finalize rather than looping forever."""
    from app.graph import human
    from app.schemas.reports import FinalReport, Finding, FindingTag

    state = new_state("CP2-CAP-TEST", "test request")
    state["final_report"] = FinalReport(
        title="T", executive_summary="x", research_objective="x", methodology="x",
        findings=[Finding(tag=FindingTag.EVIDENCE, text="x")], risks_and_limitations="x",
        recommendation="x", evidence_references=[],
    )
    state["max_revisions"] = 2
    state["revision_count"] = 2

    result = human.checkpoint_final_review(state, lambda name, payload: {"decision": "request_changes"})
    assert "revision_count" not in result  # unchanged — cap already reached
    merged_state = {**state, **result}
    assert routing.route_after_final_checkpoint(merged_state) == "finalize"


def test_writer_handles_missing_findings_key_without_crashing():
    """Regression test: a live LLM response missing the 'findings' key
    entirely previously raised an uncaught KeyError that crashed the whole
    run thread instead of failing the workflow cleanly."""
    from app.agents import writer
    from app.schemas.reports import AnalysisOutput

    state = new_state("WRITER-TEST-1", "Compare vector databases for RAG.")
    state["research_objective"] = {"objective": "Compare vector DBs"}
    state["analysis"] = AnalysisOutput(
        comparison_framework="x", conclusions=["a"], evidence_refs=["EV-1"], assumptions=[], known_gaps=[]
    )
    missing_findings = json.dumps({
        "title": "R", "executive_summary": "x", "research_objective": "x", "methodology": "x",
        "risks_and_limitations": "x", "recommendation": "x", "evidence_references": ["EV-1"],
    })
    with patch(
        "app.services.llm_client.llm_client.complete",
        return_value=LLMResult(text=missing_findings, mode="live"),
    ):
        result = writer.generate_report(state)
    assert result["workflow_status"] == WorkflowStatus.FAILED
    assert result["errors"][0]["type"] == "invalid_structured_output"


def test_writer_handles_wrong_shaped_finding_without_crashing():
    """Regression test: a finding given as a plain string instead of a
    {tag, text} object previously raised an uncaught TypeError."""
    from app.agents import writer
    from app.schemas.reports import AnalysisOutput

    state = new_state("WRITER-TEST-2", "Compare vector databases for RAG.")
    state["research_objective"] = {"objective": "Compare vector DBs"}
    state["analysis"] = AnalysisOutput(
        comparison_framework="x", conclusions=["a"], evidence_refs=["EV-1"], assumptions=[], known_gaps=[]
    )
    bad_shape = json.dumps({
        "title": "R", "executive_summary": "x", "research_objective": "x", "methodology": "x",
        "findings": ["a plain string, not a {tag, text} object"], "risks_and_limitations": "x",
        "recommendation": "x", "evidence_references": ["EV-1"],
    })
    with patch(
        "app.services.llm_client.llm_client.complete",
        return_value=LLMResult(text=bad_shape, mode="live"),
    ):
        result = writer.generate_report(state)
    assert result["workflow_status"] == WorkflowStatus.FAILED
    assert result["errors"][0]["type"] == "invalid_structured_output"


def test_writer_recovers_after_one_malformed_response():
    """Regression test: like analyze_request, generate_report should
    retry once and recover if the first attempt is malformed but a
    subsequent attempt succeeds."""
    from app.agents import writer
    from app.schemas.reports import AnalysisOutput

    state = new_state("WRITER-TEST-3", "Compare vector databases for RAG.")
    state["research_objective"] = {"objective": "Compare vector DBs"}
    state["analysis"] = AnalysisOutput(
        comparison_framework="x", conclusions=["a"], evidence_refs=["EV-1"], assumptions=[], known_gaps=[]
    )
    bad = json.dumps({"title": "R", "executive_summary": "x"})
    good = json.dumps({
        "title": "Vector DB Report", "executive_summary": "x", "research_objective": "x", "methodology": "x",
        "findings": [{"tag": "evidence", "text": "x"}], "risks_and_limitations": "x",
        "recommendation": "x", "evidence_references": ["EV-1"],
    })
    with patch(
        "app.services.llm_client.llm_client.complete",
        side_effect=[LLMResult(text=bad, mode="live"), LLMResult(text=good, mode="live")],
    ):
        result = writer.generate_report(state)
    assert result["workflow_status"] != WorkflowStatus.FAILED
    assert result["final_report"].title == "Vector DB Report"
