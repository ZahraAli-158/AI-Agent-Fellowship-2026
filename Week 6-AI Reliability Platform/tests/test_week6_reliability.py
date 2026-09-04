"""Week 6 — retry, timeout, loop-prevention, and graceful-degradation tests."""
import time
import pytest

from app.reliability.retries import call_with_retry, is_retryable, RetryExhausted
from app.reliability.timeouts import call_with_timeout, OperationTimeout
from app.reliability.loop_prevention import AgentLoopGuard, LoopLimitExceeded
from app.reliability.fallback import safe_retrieval, safe_model_call, safe_tool_call


def test_retryable_error_is_classified_retryable():
    assert is_retryable(TimeoutError("timed out"))
    assert is_retryable(Exception("429 rate limit exceeded"))


def test_non_retryable_error_is_classified_non_retryable():
    assert not is_retryable(ValueError("invalid argument: missing required field"))
    assert not is_retryable(Exception("permission denied"))


def test_call_with_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("timed out")
        return "ok"

    result = call_with_retry(flaky, max_retries=5, base_delay=0.01, jitter=False)
    assert result == "ok"
    assert calls["n"] == 3


def test_call_with_retry_does_not_retry_non_retryable_errors():
    calls = {"n": 0}

    def bad():
        calls["n"] += 1
        raise ValueError("invalid argument: bad input")

    with pytest.raises(ValueError):
        call_with_retry(bad, max_retries=5, base_delay=0.01)
    assert calls["n"] == 1  # no retries attempted


def test_call_with_retry_raises_after_exhausting_retries():
    def always_fails():
        raise TimeoutError("timed out")

    with pytest.raises(TimeoutError):
        call_with_retry(always_fails, max_retries=2, base_delay=0.01, jitter=False)


def test_call_with_timeout_returns_result_when_fast_enough():
    result = call_with_timeout(lambda: "done", operation="tool_call", timeout_s=1.0)
    assert result == "done"


def test_call_with_timeout_raises_when_too_slow():
    def slow():
        time.sleep(0.5)
        return "done"

    with pytest.raises(OperationTimeout):
        call_with_timeout(slow, operation="tool_call", timeout_s=0.05)


def test_loop_guard_raises_after_max_steps():
    guard = AgentLoopGuard(max_steps=3)
    guard.record_step()
    guard.record_step()
    guard.record_step()
    with pytest.raises(LoopLimitExceeded):
        guard.record_step()


def test_loop_guard_raises_on_duplicate_action():
    guard = AgentLoopGuard(max_tool_calls=10)
    guard.record_tool_call("create_task", "title=Foo")
    with pytest.raises(LoopLimitExceeded):
        guard.record_tool_call("create_task", "title=Foo")


def test_loop_guard_allows_distinct_actions():
    guard = AgentLoopGuard(max_tool_calls=10)
    guard.record_tool_call("create_task", "title=Foo")
    guard.record_tool_call("create_task", "title=Bar")  # different args -> not a duplicate
    assert guard.tool_calls == 2


def test_loop_guard_raises_after_max_revisions():
    guard = AgentLoopGuard(max_revisions=2)
    guard.record_revision()
    guard.record_revision()
    with pytest.raises(LoopLimitExceeded):
        guard.record_revision()


def test_safe_retrieval_degrades_gracefully_on_failure():
    def broken_retrieval():
        raise ConnectionError("vector db down")

    chunks, degraded, message = safe_retrieval(broken_retrieval)
    assert chunks == []
    assert degraded is True
    assert message is not None


def test_safe_retrieval_passes_through_on_success():
    chunks, degraded, message = safe_retrieval(lambda: ["chunk1"])
    assert chunks == ["chunk1"]
    assert degraded is False


def test_safe_model_call_falls_back_on_primary_failure():
    def primary():
        raise ConnectionError("primary model unavailable")

    result, used_fallback = safe_model_call(primary, lambda: "fallback answer")
    assert result == "fallback answer"
    assert used_fallback is True


def test_safe_tool_call_returns_partial_result_on_failure():
    def broken_tool():
        raise RuntimeError("tool exploded")

    result = safe_tool_call(broken_tool)
    assert result["status"] == "failed"
    assert result["partial"] is True
