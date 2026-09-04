"""Week 6 §19/§20 — structured logging event coverage and dashboard metric
completeness tests."""
import logging

from app.observability.logging import log_structured, EVENT_TYPES
from app.observability.metrics import reliability_summary, usage_summary
from app.observability.cost import aggregate_cost


def test_all_required_event_types_are_defined():
    required = {"request_received", "model_called", "retrieval_started", "retrieval_completed",
                 "tool_selected", "tool_succeeded", "tool_failed", "retry_attempted",
                 "guardrail_triggered", "evaluation_completed", "request_completed"}
    assert required.issubset(EVENT_TYPES)


def test_log_structured_emits_json_line(caplog):
    with caplog.at_level(logging.INFO, logger="ai_platform.events"):
        log_structured("request_received", workspace_id=1, chars=42)
    assert any("request_received" in record.message for record in caplog.records)


def test_reliability_summary_computes_timeout_rate():
    traces = [
        {"final_outcome": "failure", "error_status": "OperationTimeout: 'tool_call' exceeded its 10.0s timeout",
          "tool_calls": []},
        {"final_outcome": "success", "error_status": "", "tool_calls": []},
    ]
    summary = reliability_summary(traces)
    assert summary["timeout_rate"] == 0.5


def test_usage_summary_reports_input_output_and_total_tokens_and_requests():
    traces = [{"input_tokens": 10, "output_tokens": 20}, {"input_tokens": 5, "output_tokens": 15}]
    summary = usage_summary(traces)
    assert summary["requests"] == 2
    assert summary["input_tokens"] == 15
    assert summary["output_tokens"] == 35
    assert summary["total_tokens"] == 50


def test_aggregate_cost_reports_average_cost_per_request():
    records = [{"input_tokens": 1000, "output_tokens": 1000}, {"input_tokens": 1000, "output_tokens": 1000}]
    summary = aggregate_cost(records)
    assert "avg_cost_per_request" in summary
    assert summary["avg_cost_per_request"] == summary["total_estimated_cost"] / 2


def test_dashboard_shows_p50_input_output_tokens_and_avg_cost(client):
    from tests.conftest import register, login
    register(client)
    login(client)
    resp = client.get("/observability/")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "P50" in body
    assert "Input tokens" in body
    assert "Output tokens" in body
    assert "Avg cost" in body or "Average cost" in body
    assert "Timeout rate" in body


def test_dashboard_shows_rag_and_agent_evaluation_breakdown(client):
    from tests.conftest import register, login
    register(client)
    login(client)
    resp = client.get("/observability/")
    body = resp.data.decode()
    assert "RAG" in body
    assert "Agent" in body


def test_dashboard_shows_cost_and_latency_breakdowns(client):
    from tests.conftest import register, login
    register(client)
    login(client)
    resp = client.get("/observability/")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Cost by model" in body
    assert "Cost by agent" in body
    assert "Cost by feature" in body
    assert "Latency by pipeline stage" in body


def test_dashboard_shows_failure_code_breakdown(client):
    from tests.conftest import register, login
    register(client)
    login(client)
    resp = client.get("/observability/")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Failures by code" in body


def test_reliability_summary_counts_active_errors():
    import datetime
    now = datetime.datetime.utcnow()
    traces = [
        {"final_outcome": "failure", "tool_calls": [], "created_at": now},
        {"final_outcome": "failure", "tool_calls": [],
          "created_at": now - datetime.timedelta(hours=48)},  # outside 24h window
        {"final_outcome": "success", "tool_calls": [], "created_at": now},
    ]
    summary = reliability_summary(traces, active_error_window_hours=24)
    assert summary["failed_requests"] == 2
    assert summary["active_errors"] == 1


def test_call_counts_separates_model_and_tool_calls():
    from app.observability.metrics import call_counts
    steps_by_trace_id = {
        1: [{"step_type": "model_call"}, {"step_type": "tool_call"}, {"step_type": "tool_call"}],
        2: [{"step_type": "model_call"}],
    }
    result = call_counts(steps_by_trace_id)
    assert result["model_calls"] == 2
    assert result["tool_calls"] == 2


def test_dashboard_shows_active_errors_and_call_counts(client):
    from tests.conftest import register, login
    register(client)
    login(client)
    resp = client.get("/observability/")
    body = resp.data.decode()
    assert "Active errors" in body
    assert "Model calls" in body
    assert "Tool calls" in body
