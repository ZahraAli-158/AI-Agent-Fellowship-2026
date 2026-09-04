# Week 6 §29-33 — Reliability Engineering (Failure Injection, Retries, Timeouts, Loop Prevention, Graceful Degradation)

## §29 Failure Injection — documented system behavior

All 9 scenarios the spec lists are intentionally triggered in
`tests/test_week6_failure_injection.py` (10 tests) and
`tests/test_week6_reliability.py`, against the real code paths (not
mocks-of-mocks) in `app/reliability/`. Documented behavior for each:

| Scenario | System behavior | Test |
|---|---|---|
| LLM API unavailable | `safe_model_call()` falls back to a secondary callable instead of raising to the caller; in `chat_routes.py` the primary call is additionally retried first (`call_with_retry`) before this fallback would trigger | `test_llm_api_unavailable_falls_back_gracefully` |
| Vector database unavailable | `safe_retrieval()` returns an empty result set + a clear "temporarily unavailable" message instead of crashing; wired live into `chat_routes.py`'s retrieval block | `test_vector_db_unavailable_degrades_instead_of_crashing` |
| Tool throws exception | `safe_tool_call()` catches it and returns `{"status": "failed", "partial": True, "message": ...}` instead of aborting the whole agent turn | `test_tool_throws_exception_returns_partial_result` |
| Tool returns empty result | `safe_tool_call()` returns `{"status": "ok", "result": [], "partial": False}` — an empty result is not itself an error | `test_tool_returns_empty_result_is_handled` |
| Tool takes too long | `call_with_timeout(..., operation="tool_call")` raises `OperationTimeout` after the configured bound (10s default) instead of hanging | `test_tool_takes_too_long_times_out_instead_of_hanging` |
| Invalid JSON returned | `evaluation/judge.py`'s JSON parsing catches `JSONDecodeError` and falls back to the heuristic scorer with `judge_mode: "heuristic_fallback_parse_error"` rather than crashing the evaluation run | `test_invalid_json_from_model_does_not_crash_judge` |
| Database connection fails | A `Trace`/`TraceStep` DB commit failure is caught inside `Tracer` itself (`except Exception: logger.exception(...); db.session.rollback()`) so tracing can never take down the request it's instrumenting | `test_database_connection_failure_is_isolated_from_request` |
| Rate limit reached | `is_retryable()` classifies "429"/"rate limit" messages as retryable; `call_with_retry` retries with exponential backoff and succeeds once the simulated rate limit clears | `test_rate_limit_reached_is_retried_then_recovers` |
| Agent enters repeated loop | `AgentLoopGuard.record_tool_call()` raises `LoopLimitExceeded` on a duplicate `(tool, args)` pair or once `max_tool_calls`/`max_steps` is exceeded, producing a controlled failure instead of an unbounded loop | `test_agent_enters_repeated_loop_is_stopped`, `test_loop_guard_raises_on_duplicate_action` |

## §30 Retry Strategy — decisions and rationale

Implementation: `app/reliability/retries.py`.

**Classification** (`is_retryable(exc)`):

| Retryable | Non-retryable |
|---|---|
| `TimeoutError`, `ConnectionError` (by type) | Any message containing "invalid argument" |
| Any message containing "rate limit", "timeout", "temporarily unavailable", "429", "503" | Any message containing "unauthorized", "permission denied" |
| | Any message containing "missing required", "validation error" |
| | Anything not explicitly matched above (fail closed — don't retry unknown errors, since retrying an unclassified failure risks masking a real bug) |

**Configuration:**

| Setting | Value | Where | Rationale |
|---|---|---|---|
| Max retries | 2 (chat model calls), 3 (default in `call_with_retry`, used elsewhere) | `chat_routes.send_message` | Chat is user-facing and latency-sensitive — 2 retries (3 total attempts) bounds worst-case added latency to a few seconds while still recovering from a single transient blip |
| Retry delay (base) | 0.5s | same | Short enough not to noticeably stall a chat response, long enough to let a brief rate-limit window pass |
| Backoff strategy | Exponential (`base_delay * 2^attempt`) + random jitter (`+ uniform(0, base_delay)`) | `call_with_retry(backoff="exponential", jitter=True)` (both are the defaults) | Exponential backoff avoids hammering an already-struggling API; jitter avoids many concurrent requests retrying in lockstep and re-triggering the same rate limit together |

Every retry attempt is logged as a structured `retry_attempted` event
(§19) with the attempt number and the triggering error, so retry
frequency is visible on the observability dashboard's "Retry rate" metric.

## §31 Timeout Handling

Implementation: `app/reliability/timeouts.py` (`call_with_timeout`, thread-pool based so it works cross-platform, including the Windows dev environment this project also runs on — `signal.alarm` is Unix-only).

| Operation | Default timeout | Wired into |
|---|---|---|
| Model calls | 20s | `chat_routes.send_message` (each retry attempt individually time-boxed) |
| Tool calls | 10s | `app.reliability.fallback.safe_tool_call` callers |
| Retrieval | 8s | `chat_routes.send_message`'s retrieval block, combined with `safe_retrieval` for graceful degradation on either a timeout or a hard failure |
| Long-running workflow steps | 30s | `agent_service.run_agent_turn`'s model/function-calling turn (`operation="workflow_step"`) |

A timed-out operation raises `OperationTimeout`, which is caught by the
surrounding `safe_retrieval`/`safe_model_call`/generic exception handler at
each call site and turned into a controlled, user-facing message — never
an unhandled hang.

## §32 Agent Loop Prevention

Implementation: `app/reliability/loop_prevention.py` (`AgentLoopGuard`), wired live into `agent_service.run_agent_turn`.

| Control | Default | Behavior when exceeded |
|---|---|---|
| Maximum agent steps | 12 | `LoopLimitExceeded` |
| Maximum tool calls | 8 | `LoopLimitExceeded` |
| Duplicate action detection | any repeated `(tool_name, args)` pair | `LoopLimitExceeded` immediately, even under the max-calls limit |
| Maximum revision cycles | 3 (infrastructure only — see note) | `LoopLimitExceeded` |
| Execution timeout | 30s (`operation="workflow_step"`) | `OperationTimeout`, caught and turned into `[Agent error: ...]` |

**Honest note on revision cycles:** the Meeting Agent
(`app/services/agent_service.py`) is a single-turn tool-calling agent with
no self-critique/revise loop of its own — `record_revision()` exists as
general-purpose infrastructure (documented in the class docstring) for a
future workflow that does have one (the separate Week 4 MADIP project's
Critic-revise pattern is the closest existing example in this codebase),
but is never called in the current live path. This mirrors the same honest
scoping applied to multi-agent metrics in
`docs/WEEK6_AGENT_EVALUATION.md`.

When any limit is exceeded, `run_agent_turn` surfaces a controlled failure
(a normal error response) rather than allowing the loop to continue —
verified by `test_agent_enters_repeated_loop_is_stopped` and
`test_loop_guard_raises_after_max_steps`.

## §33 Graceful Degradation — 3 documented scenarios

See `docs/WEEK6_REPORT.md` §4 for the full writeup; summary:

1. **Vector DB / retrieval failure** → `safe_retrieval()`, live in `chat_routes.py`.
2. **Primary model failure** → `safe_model_call()`.
3. **Tool failure** → `safe_tool_call()`.

All three are unit-tested and (1) is also wired into the live chat route
with timeout protection (§31) on top of the failure handling.
