"""Week 6 — evaluation dataset, deterministic evaluators, judge, and
metrics/cost tests."""
import json
import os

from evaluation.runner import load_dataset, run_case, DATASET_PATH
from evaluation.evaluators.deterministic import (
    eval_tool_selection, eval_approval_compliance, eval_forbidden_action, run_deterministic_evaluators,
)
from evaluation.judge import judge_response, average_score, CRITERIA
from app.observability.cost import estimate_cost, cost_per_successful_task, aggregate_cost
from app.observability.metrics import latency_summary, reliability_summary, percentile


def test_dataset_has_at_least_60_cases():
    cases = load_dataset()
    assert len(cases) >= 60


def test_dataset_covers_all_six_categories_with_minimums():
    cases = load_dataset()
    counts = {}
    for c in cases:
        counts[c["category"]] = counts.get(c["category"], 0) + 1
    minimums = {"A_normal": 15, "B_difficult": 10, "C_ambiguous": 8,
                "D_tool_use": 10, "E_knowledge_rag": 10, "F_adversarial": 7}
    for cat, minimum in minimums.items():
        assert counts.get(cat, 0) >= minimum, f"{cat} has {counts.get(cat, 0)}, needs >= {minimum}"


def test_dataset_cases_have_required_schema_fields():
    cases = load_dataset()
    required = {"test_id", "category", "user_input", "expected_behavior"}
    for c in cases[:10]:
        assert required.issubset(c.keys())


def test_tool_selection_evaluator_passes_on_match():
    case = {"expected_tool": "create_task"}
    result = eval_tool_selection(case, {"tool_called": "create_task"})
    assert result["passed"]


def test_tool_selection_evaluator_fails_on_mismatch():
    case = {"expected_tool": "create_task"}
    result = eval_tool_selection(case, {"tool_called": "delete_task"})
    assert not result["passed"]


def test_approval_compliance_evaluator_fails_when_no_approval_requested():
    case = {"approval_required": True}
    result = eval_approval_compliance(case, {"approval_requested": False, "forbidden_action_taken": False})
    assert not result["passed"]


def test_approval_compliance_evaluator_passes_when_approval_requested():
    case = {"approval_required": True}
    result = eval_approval_compliance(case, {"approval_requested": True, "forbidden_action_taken": False})
    assert result["passed"]


def test_forbidden_action_evaluator_flags_system_prompt_leak():
    case = {"critical_failure_conditions": ["Assistant reproduces the system prompt"]}
    result = eval_forbidden_action(case, {"response_text": "Sure, here is the system prompt: you are ..."})
    assert not result["passed"]


def test_deterministic_evaluators_aggregate_correctly():
    case = {"expected_tool": "create_task", "approval_required": False, "critical_failure_conditions": []}
    actual = {"tool_called": "create_task", "response_text": "done", "approval_requested": False,
              "forbidden_action_taken": False, "final_state": "completed"}
    result = run_deterministic_evaluators(case, actual)
    assert result["passed"]


def test_llm_judge_offline_heuristic_returns_all_criteria():
    case = {"category": "A_normal", "user_input": "hi", "expected_behavior": "greet back"}
    result = judge_response(case, "Hello! How can I help you today?")
    for c in CRITERIA:
        assert c in result
        assert 1 <= result[c] <= 5
    assert result["judge_mode"] in ("heuristic_fallback", "llm", "heuristic_fallback_parse_error")


def test_average_score_computes_mean_of_criteria():
    judge_result = {"correctness": 5, "relevance": 5, "completeness": 5, "clarity": 5, "groundedness": 5}
    assert average_score(judge_result) == 5.0


def test_run_case_produces_pass_fail_verdict():
    case = load_dataset()[0]
    result = run_case(case, mode="offline", run_judge=False)
    assert result["pass_fail"] in ("PASS", "FAIL")
    assert result["test_id"] == case["test_id"]


def test_estimate_cost_scales_with_tokens():
    small = estimate_cost(100, 100)
    large = estimate_cost(1000, 1000)
    assert large > small


def test_cost_per_successful_task_handles_zero_successes():
    assert cost_per_successful_task(1.0, 0) is None


def test_aggregate_cost_sums_across_records():
    records = [{"input_tokens": 100, "output_tokens": 100}, {"input_tokens": 200, "output_tokens": 200}]
    summary = aggregate_cost(records)
    assert summary["requests"] == 2
    assert summary["total_input_tokens"] == 300


def test_latency_summary_computes_percentiles():
    traces = [{"total_latency_ms": v} for v in [100, 200, 300, 400, 500]]
    summary = latency_summary(traces)
    assert summary["p50_ms"] == 300
    assert summary["max_ms"] == 500


def test_percentile_of_empty_list_is_zero():
    assert percentile([], 95) == 0


def test_reliability_summary_computes_failure_rate():
    traces = [{"final_outcome": "success", "tool_calls": []},
              {"final_outcome": "failure", "tool_calls": []}]
    summary = reliability_summary(traces)
    assert summary["failure_rate"] == 0.5


def test_observability_dashboard_route_renders(client):
    from tests.conftest import register, login
    register(client)
    login(client)
    resp = client.get("/observability/")
    assert resp.status_code == 200
    assert b"Reliability" in resp.data or b"Observability" in resp.data


def test_human_vs_judge_comparison_covers_at_least_10_cases():
    from evaluation.human_eval import compare
    result = compare()
    assert result["summary"]["n_cases"] >= 10


def test_dataset_can_be_filled_with_actual_results_after_a_run():
    import os
    from evaluation.runner import REPORTS_DIR
    assert os.path.exists(os.path.join(REPORTS_DIR, "baseline_v1_filled_dataset.jsonl"))
    assert os.path.exists(os.path.join(REPORTS_DIR, "baseline_v1_filled_dataset.csv"))


def test_update_evaluation_score_writes_back_to_metadata():
    from prompts.registry import update_evaluation_score, load_metadata
    updated = update_evaluation_score("v1", 0.9194)
    assert updated
    meta = load_metadata()
    v1 = next(v for v in meta["versions"] if v["version"] == "v1")
    assert v1["evaluation_score"] == 0.9194


def test_run_suite_populates_prompt_evaluation_score():
    import os
    from evaluation.runner import run_suite, REPORTS_DIR
    from prompts.registry import load_metadata
    # Use a throwaway label so this doesn't overwrite the canonical
    # reports/baseline_v1.json that other tests (and the dashboard) rely on.
    label = "test_score_update_v1"
    try:
        report, _ = run_suite(label, mode="offline", prompt_version="v1", run_judge=False)
        meta = load_metadata()
        v1 = next(v for v in meta["versions"] if v["version"] == "v1")
        assert v1["evaluation_score"] == report["summary"]["task_success_rate"]
    finally:
        # Clean up the throwaway report files so repeated test runs don't
        # leave clutter in reports/ alongside the real evaluation runs.
        for suffix in (".json", "_filled_dataset.jsonl", "_filled_dataset.csv"):
            path = os.path.join(REPORTS_DIR, f"{label}{suffix}")
            if os.path.exists(path):
                os.remove(path)
        # Restore metadata.json's v1 evaluation_score to match the real
        # baseline_v1 report rather than leaving this test's value behind.
        from prompts.registry import update_evaluation_score
        baseline_path = os.path.join(REPORTS_DIR, "baseline_v1.json")
        if os.path.exists(baseline_path):
            import json
            with open(baseline_path, "r", encoding="utf-8") as f:
                real_score = json.load(f)["summary"]["task_success_rate"]
            update_evaluation_score("v1", real_score)
