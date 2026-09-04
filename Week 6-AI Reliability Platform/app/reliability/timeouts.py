"""
Timeout handling (Week 6, Requirement 18).

A failed/slow component must not freeze the whole application. Uses
concurrent.futures so it works cross-platform (signal.alarm is Unix-only,
and this codebase targets Windows dev machines too — see project memory).
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

DEFAULT_TIMEOUTS = {
    "model_call": 20.0,
    "tool_call": 10.0,
    "retrieval": 8.0,
    "workflow_step": 30.0,
}


class OperationTimeout(Exception):
    def __init__(self, operation, timeout_s):
        super().__init__(f"'{operation}' exceeded its {timeout_s}s timeout")
        self.operation = operation
        self.timeout_s = timeout_s


def call_with_timeout(fn, *args, operation="model_call", timeout_s=None, **kwargs):
    timeout_s = timeout_s or DEFAULT_TIMEOUTS.get(operation, 15.0)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn, *args, **kwargs)
        try:
            return future.result(timeout=timeout_s)
        except FutureTimeoutError:
            raise OperationTimeout(operation, timeout_s)
