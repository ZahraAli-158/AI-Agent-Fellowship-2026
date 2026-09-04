"""
Latency analysis (Week 6, Requirement 22).

Breaks end-to-end latency down by pipeline stage using Trace + TraceStep
data, computes mean/median/P50/P95 for each measurable stage, and
identifies the largest bottleneck.

Honest scoping: this platform's database is local SQLite with no separate
network hop, and individual query timings aren't instrumented at
per-statement granularity — "Database latency" is therefore reported as
`not_measured` rather than a fabricated number, with a note explaining why
(see `database_latency` below). LLM, Retrieval, Tool, and End-to-end
latency are all measured from real Trace/TraceStep data.
"""
import statistics

from app.observability.metrics import percentile


def _stage_summary(values):
    if not values:
        return {"mean_ms": None, "median_ms": None, "p50_ms": None, "p95_ms": None, "n": 0}
    sorted_vals = sorted(values)
    median = statistics.median(sorted_vals)
    return {
        "mean_ms": round(statistics.fmean(sorted_vals), 1),
        "median_ms": round(median, 1),
        "p50_ms": round(percentile(sorted_vals, 50), 1),
        "p95_ms": round(percentile(sorted_vals, 95), 1),
        "n": len(sorted_vals),
    }


def analyze_latency(traces, steps_by_trace_id=None):
    """`traces`: iterable of Trace rows/dicts. `steps_by_trace_id`: optional
    dict of trace.id -> list of TraceStep rows/dicts; when omitted, only
    the coarse per-Trace fields (total_latency_ms, retrieval_latency_ms)
    are used and tool/LLM-step-level breakdowns are skipped."""
    steps_by_trace_id = steps_by_trace_id or {}

    end_to_end = []
    retrieval = []
    llm = []
    tool = []

    for t in traces:
        get = t.get if isinstance(t, dict) else (lambda k, d=None: getattr(t, k, d))
        end_to_end.append(get("total_latency_ms", 0) or 0)
        if get("retrieval_latency_ms", 0):
            retrieval.append(get("retrieval_latency_ms", 0))

        trace_id = get("id")
        for step in steps_by_trace_id.get(trace_id, []):
            sget = step.get if isinstance(step, dict) else (lambda k, d=None: getattr(step, k, d))
            step_type = sget("step_type")
            duration = sget("duration_ms", 0) or 0
            if step_type == "model_call":
                llm.append(duration)
            elif step_type == "tool_call":
                tool.append(duration)

    stages = {
        "llm_latency": _stage_summary(llm),
        "retrieval_latency": _stage_summary(retrieval),
        "tool_latency": _stage_summary(tool),
        "database_latency": {
            "mean_ms": None, "median_ms": None, "p50_ms": None, "p95_ms": None, "n": 0,
            "note": "Not separately measured — this platform uses local SQLite with no "
                     "per-statement instrumentation; database time is included in "
                     "end-to-end latency rather than broken out.",
        },
        "end_to_end_latency": _stage_summary(end_to_end),
    }

    # Bottleneck: the measured stage (excluding end-to-end itself) with the
    # highest mean duration, as a share of end-to-end mean latency.
    measurable = {name: s for name, s in stages.items()
                   if name != "end_to_end_latency" and s.get("mean_ms") is not None}
    bottleneck = max(measurable.items(), key=lambda kv: kv[1]["mean_ms"]) if measurable else None
    end_to_end_mean = stages["end_to_end_latency"]["mean_ms"]

    return {
        "stages": stages,
        "bottleneck": {
            "stage": bottleneck[0],
            "mean_ms": bottleneck[1]["mean_ms"],
            "share_of_end_to_end": round(bottleneck[1]["mean_ms"] / end_to_end_mean, 4)
                                     if bottleneck and end_to_end_mean else None,
        } if bottleneck else None,
    }
