"""
Metrics aggregation for the Quality Dashboard (Week 6, Requirement 9 / 47).

Pure functions over lists of Trace-like dicts/rows so they're unit-testable
without a running Flask app or database.
"""
import statistics


def _latencies(traces):
    return sorted(t.get("total_latency_ms", 0) if isinstance(t, dict) else t.total_latency_ms
                   for t in traces)


def percentile(sorted_values, pct):
    if not sorted_values:
        return 0
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f, c = int(k), min(int(k) + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def latency_summary(traces):
    lat = _latencies(traces)
    if not lat:
        return {"avg_ms": 0, "p50_ms": 0, "p95_ms": 0, "min_ms": 0, "max_ms": 0}
    return {
        "avg_ms": round(statistics.fmean(lat), 1),
        "p50_ms": round(percentile(lat, 50), 1),
        "p95_ms": round(percentile(lat, 95), 1),
        "min_ms": lat[0],
        "max_ms": lat[-1],
    }


def reliability_summary(traces, active_error_window_hours=24):
    total = len(traces)
    get = lambda t, k, d=None: t.get(k, d) if isinstance(t, dict) else getattr(t, k, d)
    failed = sum(1 for t in traces if get(t, "final_outcome") == "failure")
    retried = sum(1 for t in traces
                   if any(s.get("status") == "retried" for s in (get(t, "tool_calls") or [])))
    timed_out = sum(1 for t in traces
                      if "timeout" in (get(t, "error_status") or "").lower()
                      or "timed out" in (get(t, "error_status") or "").lower())
    succeeded = total - failed

    # "Active errors" (Week 6 §47 System Health): failures within a recent
    # window, since this simple app has no incident-resolution workflow to
    # define "active" any more precisely than "recent."
    import datetime
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=active_error_window_hours)
    active_errors = 0
    for t in traces:
        if get(t, "final_outcome") != "failure":
            continue
        created_at = get(t, "created_at")
        if created_at is None or (isinstance(created_at, datetime.datetime) and created_at >= cutoff):
            active_errors += 1

    return {
        "total_requests": total,
        "successful_requests": succeeded,
        "failed_requests": failed,
        "failure_rate": round(failed / total, 4) if total else 0.0,
        "retry_rate": round(retried / total, 4) if total else 0.0,
        "timeout_rate": round(timed_out / total, 4) if total else 0.0,
        "active_errors": active_errors,
    }


def call_counts(steps_by_trace_id):
    """Week 6 §47 Usage: 'Model Calls' and 'Tool Calls' as distinct counts
    (separate from raw token usage), derived from real TraceStep rows."""
    model_calls = 0
    tool_calls = 0
    for steps in steps_by_trace_id.values():
        for step in steps:
            step_type = step.get("step_type") if isinstance(step, dict) else getattr(step, "step_type", None)
            if step_type == "model_call":
                model_calls += 1
            elif step_type == "tool_call":
                tool_calls += 1
    return {"model_calls": model_calls, "tool_calls": tool_calls}


def usage_summary(traces):
    get = lambda t, k, d=0: t.get(k, d) if isinstance(t, dict) else getattr(t, k, d)
    input_tokens = sum(get(t, "input_tokens", 0) for t in traces)
    output_tokens = sum(get(t, "output_tokens", 0) for t in traces)
    return {
        "requests": len(traces),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def group_by(traces, key_fn):
    groups = {}
    for t in traces:
        groups.setdefault(key_fn(t), []).append(t)
    return groups
