"""Week 6 §21/§34/§35/§36 — cost breakdown (by model/agent/feature,
input/output split) and latency-stage analysis tests."""
from app.observability.cost import (
    estimate_cost_breakdown, cost_by_model, cost_by_agent, cost_by_feature, cost_per_successful_task,
)
from app.observability.latency_analysis import analyze_latency


def test_estimate_cost_breakdown_splits_input_and_output():
    breakdown = estimate_cost_breakdown(1000, 1000)
    assert breakdown["input_cost"] > 0
    assert breakdown["output_cost"] > 0
    assert breakdown["total_cost"] == round(breakdown["input_cost"] + breakdown["output_cost"], 6)


def test_estimate_cost_breakdown_output_costs_more_per_token():
    # DEFAULT_OUTPUT_RATE > DEFAULT_INPUT_RATE, so equal token counts should
    # cost more on the output side.
    breakdown = estimate_cost_breakdown(1000, 1000)
    assert breakdown["output_cost"] > breakdown["input_cost"]


def test_cost_by_model_groups_correctly():
    records = [
        {"model": "gemini-3.6-flash", "input_tokens": 100, "output_tokens": 100},
        {"model": "gemini-3.6-flash", "input_tokens": 100, "output_tokens": 100},
        {"model": "gemini-flash-latest", "input_tokens": 100, "output_tokens": 100},
    ]
    result = cost_by_model(records)
    assert result["gemini-3.6-flash"]["requests"] == 2
    assert result["gemini-flash-latest"]["requests"] == 1


def test_cost_by_agent_separates_agent_and_non_agent_requests():
    records = [
        {"request_type": "agent", "agent_key": "meeting", "input_tokens": 100, "output_tokens": 100},
        {"request_type": "chat", "agent_key": None, "input_tokens": 100, "output_tokens": 100},
    ]
    result = cost_by_agent(records)
    assert "meeting" in result
    assert "(non-agent)" in result


def test_cost_by_feature_groups_by_request_type():
    records = [
        {"request_type": "chat", "input_tokens": 100, "output_tokens": 100},
        {"request_type": "rag", "input_tokens": 100, "output_tokens": 100},
        {"request_type": "agent", "input_tokens": 100, "output_tokens": 100},
    ]
    result = cost_by_feature(records)
    assert set(result.keys()) == {"chat", "rag", "agent"}


def test_cost_per_successful_task_matches_spec_example():
    # Spec §35 example: avg request cost $0.010, task success 90% ->
    # approx cost per successful task $0.011.
    total_cost = 0.010 * 100  # 100 requests at $0.010 avg
    successful = 90
    result = cost_per_successful_task(total_cost, successful)
    assert abs(result - 0.0111) < 0.001


def test_analyze_latency_computes_end_to_end_stats():
    traces = [{"id": i, "total_latency_ms": v, "retrieval_latency_ms": 0}
               for i, v in enumerate([100, 200, 300, 400, 500])]
    result = analyze_latency(traces)
    assert result["stages"]["end_to_end_latency"]["median_ms"] == 300
    assert result["stages"]["end_to_end_latency"]["mean_ms"] == 300.0


def test_analyze_latency_breaks_down_llm_and_tool_stages():
    traces = [{"id": 1, "total_latency_ms": 500, "retrieval_latency_ms": 50}]
    steps_by_trace_id = {
        1: [
            {"step_type": "model_call", "duration_ms": 300},
            {"step_type": "tool_call", "duration_ms": 100},
            {"step_type": "tool_call", "duration_ms": 50},
        ]
    }
    result = analyze_latency(traces, steps_by_trace_id)
    assert result["stages"]["llm_latency"]["mean_ms"] == 300.0
    assert result["stages"]["tool_latency"]["mean_ms"] == 75.0
    assert result["stages"]["retrieval_latency"]["mean_ms"] == 50.0


def test_analyze_latency_database_latency_honestly_unmeasured():
    result = analyze_latency([{"id": 1, "total_latency_ms": 100, "retrieval_latency_ms": 0}])
    assert result["stages"]["database_latency"]["mean_ms"] is None
    assert "note" in result["stages"]["database_latency"]


def test_analyze_latency_identifies_bottleneck():
    traces = [{"id": 1, "total_latency_ms": 1000, "retrieval_latency_ms": 50}]
    steps_by_trace_id = {
        1: [
            {"step_type": "model_call", "duration_ms": 800},
            {"step_type": "tool_call", "duration_ms": 50},
        ]
    }
    result = analyze_latency(traces, steps_by_trace_id)
    assert result["bottleneck"]["stage"] == "llm_latency"


def test_analyze_latency_handles_no_traces():
    result = analyze_latency([])
    assert result["stages"]["end_to_end_latency"]["n"] == 0
    assert result["bottleneck"] is None
