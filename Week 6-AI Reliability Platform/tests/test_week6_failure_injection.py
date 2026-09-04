"""Week 6, Requirement 16 — Failure Injection.

Intentionally breaks components (model API, DB, tools) to verify the
platform degrades gracefully instead of crashing or hanging.
"""
import pytest
from unittest.mock import patch

from app.reliability.fallback import safe_retrieval, safe_model_call, safe_tool_call
from app.reliability.timeouts import call_with_timeout, OperationTimeout
from app.reliability.retries import call_with_retry, RetryExhausted
from app.reliability.loop_prevention import AgentLoopGuard, LoopLimitExceeded


def test_llm_api_unavailable_falls_back_gracefully():
    def primary():
        raise ConnectionError("LLM API unavailable")

    result, used_fallback = safe_model_call(primary, lambda: "fallback response")
    assert used_fallback
    assert result == "fallback response"


def test_vector_db_unavailable_degrades_instead_of_crashing():
    def broken_search():
        raise ConnectionError("vector database unreachable")

    chunks, degraded, message = safe_retrieval(broken_search)
    assert degraded
    assert chunks == []
    assert "temporarily unavailable" in message


def test_tool_throws_exception_returns_partial_result():
    def broken_tool(**kwargs):
        raise RuntimeError("tool crashed")

    result = safe_tool_call(broken_tool, task_id=5)
    assert result["status"] == "failed"
    assert result["partial"] is True


def test_tool_returns_empty_result_is_handled():
    def empty_tool():
        return []

    result = safe_tool_call(empty_tool)
    assert result["status"] == "ok"
    assert result["result"] == []


def test_tool_takes_too_long_times_out_instead_of_hanging():
    import time

    def slow_tool():
        time.sleep(2)
        return "too late"

    with pytest.raises(OperationTimeout):
        call_with_timeout(slow_tool, operation="tool_call", timeout_s=0.05)


def test_invalid_json_from_model_does_not_crash_judge():
    from evaluation.judge import judge_response
    case = {"category": "A_normal", "user_input": "hi", "expected_behavior": "greet"}
    with patch("app.services.gemini_service.is_configured", return_value=True), \
         patch("app.services.gemini_service.chat_completion",
               return_value={"text": "not valid json at all {{{"}):
        result = judge_response(case, "hello")
        assert result["judge_mode"] == "heuristic_fallback_parse_error"


def test_database_connection_failure_is_isolated_from_request(app):
    """Tracing must never crash the caller even if the DB write fails."""
    from app.observability.tracing import Tracer
    with app.app_context():
        with patch("app.models.models.db.session.commit", side_effect=Exception("db connection failed")):
            # Should not raise, despite the DB commit failing internally.
            with Tracer(request_type="chat", input_text="test") as t:
                t.set_output("response text")
        assert True  # reaching this line means the failure was contained


def test_rate_limit_reached_is_retried_then_recovers():
    calls = {"n": 0}

    def rate_limited():
        calls["n"] += 1
        if calls["n"] < 2:
            raise Exception("429 rate limit reached")
        return "success after rate limit"

    result = call_with_retry(rate_limited, max_retries=3, base_delay=0.01, jitter=False)
    assert result == "success after rate limit"


def test_agent_enters_repeated_loop_is_stopped():
    guard = AgentLoopGuard(max_tool_calls=3)
    with pytest.raises(LoopLimitExceeded):
        for _ in range(5):
            guard.record_tool_call("search_knowledge_base", f"query={_}")  # distinct args each time


def test_non_retryable_failure_does_not_retry_forever():
    calls = {"n": 0}

    def bad_args():
        calls["n"] += 1
        raise ValueError("invalid argument: task_id must be an integer")

    with pytest.raises(ValueError):
        call_with_retry(bad_args, max_retries=5, base_delay=0.01)
    assert calls["n"] == 1
