"""Week 6 §14/§15/§16 — RAG evaluation, RAG failure classification, and
agent evaluation module tests."""
from evaluation.evaluators.rag_eval import (
    retrieval_hit_rate, context_relevance, citation_correctness,
    classify_rag_failure, aggregate_rag_metrics, is_rag_case,
)
from evaluation.evaluators.agent_eval import (
    eval_intent_understanding, eval_planning, eval_recovery_behavior,
    run_agent_evaluators, aggregate_agent_metrics, MULTI_AGENT_METRICS,
)


def _rag_case(expected_source):
    return {"category": "E_knowledge_rag", "expected_source": expected_source, "test_id": "EX"}


def test_non_rag_case_returns_none_for_all_rag_metrics():
    case = {"category": "A_normal"}
    assert retrieval_hit_rate(case, {}) is None
    assert context_relevance(case, {}) is None
    assert is_rag_case(case) is False


def test_retrieval_hit_rate_true_when_expected_docs_present():
    case = _rag_case(["doc1.txt"])
    actual = {"retrieved_doc_ids": ["doc1.txt", "doc2.txt"]}
    assert retrieval_hit_rate(case, actual) is True


def test_retrieval_hit_rate_false_when_expected_doc_missing():
    case = _rag_case(["doc1.txt"])
    actual = {"retrieved_doc_ids": ["doc2.txt"]}
    assert retrieval_hit_rate(case, actual) is False


def test_retrieval_hit_rate_true_for_correctly_empty_retrieval():
    case = _rag_case([])  # nothing should be retrieved
    actual = {"retrieved_doc_ids": []}
    assert retrieval_hit_rate(case, actual) is True


def test_context_relevance_computes_precision():
    case = _rag_case(["doc1.txt"])
    actual = {"retrieved_doc_ids": ["doc1.txt", "doc2.txt"]}
    assert context_relevance(case, actual) == 0.5


def test_citation_correctness_flags_citation_not_in_retrieved_set():
    case = _rag_case(["doc1.txt"])
    actual = {"citations": ["doc3.txt"], "retrieved_doc_ids": ["doc1.txt"]}
    assert citation_correctness(case, actual) == 0.0


def test_classify_rag_failure_retrieval_failure_when_info_missing():
    case = _rag_case(["doc1.txt"])
    actual = {"retrieved_doc_ids": [], "response_text": "some answer"}
    assert classify_rag_failure(case, actual) == "retrieval_failure"


def test_classify_rag_failure_generation_failure_when_retrieval_ok_but_ungrounded():
    case = _rag_case(["doc1.txt"])
    actual = {"retrieved_doc_ids": ["doc1.txt"], "response_text": "made up answer"}
    judge_result = {"groundedness": 1}  # very low groundedness -> normalized 0.0
    assert classify_rag_failure(case, actual, judge_result) == "generation_failure"


def test_classify_rag_failure_success_when_both_stages_ok():
    case = _rag_case(["doc1.txt"])
    actual = {"retrieved_doc_ids": ["doc1.txt"], "response_text": "grounded answer"}
    judge_result = {"groundedness": 5}
    assert classify_rag_failure(case, actual, judge_result) == "success"


def test_classify_rag_failure_not_applicable_for_non_rag_case():
    assert classify_rag_failure({"category": "A_normal"}, {}) == "not_applicable"


def test_aggregate_rag_metrics_reports_failure_breakdown():
    results = [
        {"retrieval_hit_rate": True, "context_relevance": 1.0, "answer_groundedness": 0.8,
          "citation_correctness": 1.0, "rag_failure_class": "success"},
        {"retrieval_hit_rate": False, "context_relevance": 0.0, "answer_groundedness": None,
          "citation_correctness": None, "rag_failure_class": "retrieval_failure"},
    ]
    summary = aggregate_rag_metrics(results)
    assert summary["n_rag_cases"] == 2
    assert summary["failure_breakdown"] == {"success": 1, "retrieval_failure": 1}


def test_intent_understanding_flags_missed_clarification_on_ambiguous_case():
    case = {"category": "C_ambiguous", "test_id": "CX"}
    actual = {"final_state": "completed"}  # should have asked for clarification
    result = eval_intent_understanding(case, actual)
    assert not result["passed"]


def test_intent_understanding_passes_when_ambiguous_case_asks_for_clarification():
    case = {"category": "C_ambiguous", "test_id": "CX"}
    actual = {"final_state": "clarification_requested"}
    result = eval_intent_understanding(case, actual)
    assert result["passed"]


def test_planning_not_scored_for_non_tool_difficult_cases():
    case = {"category": "B_difficult", "test_id": "B02", "expected_tool": None}
    result = eval_planning(case, {"response_text": "[baseline offline response] whatever"})
    assert result["passed"]  # not scored -> auto-pass, per docstring


def test_planning_flags_fallback_on_tool_requiring_case():
    case = {"category": "B_difficult", "test_id": "B01", "expected_tool": "create_task"}
    result = eval_planning(case, {"response_text": "[baseline offline response] whatever"})
    assert not result["passed"]


def test_recovery_behavior_passes_on_clarification_request():
    case = {"test_id": "D06"}
    actual = {"final_state": "clarification_requested", "tool_args": {"due_date": "45th of Marchtember"}}
    result = eval_recovery_behavior(case, actual)
    assert result["passed"]


def test_recovery_behavior_fails_when_bad_value_silently_used():
    case = {"test_id": "D07"}
    actual = {"final_state": "completed", "tool_args": {"task_id": "abc"}}
    result = eval_recovery_behavior(case, actual)
    assert not result["passed"]


def test_run_agent_evaluators_aggregates_pass_fail():
    case = {"category": "A_normal", "test_id": "A01"}
    actual = {"final_state": "completed", "tool_called": "create_task", "response_text": "ok"}
    result = run_agent_evaluators(case, actual)
    assert "passed" in result and "loop_frequency" in result


def test_multi_agent_metrics_explicitly_marked_not_applicable():
    assert MULTI_AGENT_METRICS["applicable"] is False
    assert MULTI_AGENT_METRICS["agent_routing_accuracy"] is None


def test_aggregate_agent_metrics_computes_avg_loop_frequency():
    agent_results = [
        {"passed": True, "checks": {"x": {"passed": True}}, "loop_frequency": 1},
        {"passed": True, "checks": {"x": {"passed": True}}, "loop_frequency": 3},
    ]
    summary = aggregate_agent_metrics(agent_results)
    assert summary["avg_loop_frequency"] == 2.0
