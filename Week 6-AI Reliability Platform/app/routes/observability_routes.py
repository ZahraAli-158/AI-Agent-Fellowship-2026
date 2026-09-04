"""
Week 6, Requirements 9/18/47 — the Quality/Observability Dashboard and
Trace Viewer, as a platform-wide blueprint (not scoped to one workspace,
since traces/evaluations span the whole account).
"""
import json
import os

from flask import Blueprint, render_template, jsonify, current_app
from flask_login import login_required, current_user

from app.models.models import db, Trace, TraceStep, GuardrailEvent, EvalRun
from app.observability.metrics import latency_summary, reliability_summary, usage_summary, call_counts
from app.observability.cost import aggregate_cost, cost_per_successful_task, cost_by_model, cost_by_agent, cost_by_feature
from app.observability.latency_analysis import analyze_latency

observability_bp = Blueprint("observability", __name__, url_prefix="/observability")


@observability_bp.route("/")
@login_required
def view_dashboard():
    traces = Trace.query.filter_by(user_id=current_user.id).order_by(Trace.created_at.desc()).limit(500).all()

    lat = latency_summary(traces)
    rel = reliability_summary(traces)
    usage = usage_summary(traces)
    cost = aggregate_cost(traces)
    cost_model_breakdown = cost_by_model(traces)
    cost_agent_breakdown = cost_by_agent(traces)
    cost_feature_breakdown = cost_by_feature(traces)

    steps_by_trace_id = {}
    if traces:
        trace_ids = [t.id for t in traces]
        for step in TraceStep.query.filter(TraceStep.trace_id.in_(trace_ids)).all():
            steps_by_trace_id.setdefault(step.trace_id, []).append(step)
    latency_breakdown = analyze_latency(traces, steps_by_trace_id)
    calls = call_counts(steps_by_trace_id)

    guardrail_events = (GuardrailEvent.query.order_by(GuardrailEvent.created_at.desc()).limit(50).all())
    injection_attempts = sum(1 for g in guardrail_events if "prompt_injection" in g.rule)
    unauthorized_attempts = sum(1 for g in guardrail_events if "unauthorized" in g.rule or "approval" in g.rule)

    eval_runs = EvalRun.query.order_by(EvalRun.created_at.desc()).limit(20).all()
    # Pick up the latest generated report files too, in case the CLI runner
    # was used directly (evaluation/runner.py) rather than through the app.
    reports_dir = os.path.join(current_app.root_path, "..", "reports")
    report_summaries = []
    if os.path.isdir(reports_dir):
        for fname in sorted(os.listdir(reports_dir)):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(reports_dir, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    summary = data.get("summary")
                    # Only genuine evaluation-run summaries belong on this table (skip
                    # sibling reports like human_vs_judge_comparison.json, which has a
                    # differently-shaped "summary").
                    if summary and "task_success_rate" in summary:
                        report_summaries.append(summary)
                except (json.JSONDecodeError, KeyError, OSError):
                    continue

    # Week 6 §20: "Display metrics by Model / Prompt version / Date / Test
    # category, where practical." Live traces group naturally by model and
    # by date; prompt version and test category are properties of an
    # evaluation RUN rather than a single trace, so those are broken out
    # from report_summaries (by run/prompt-version) and from the latest
    # report's by_category breakdown, respectively.
    by_model = {}
    by_date = {}
    for t in traces:
        m = t.model or "(unknown)"
        by_model.setdefault(m, {"requests": 0, "total_latency_ms": 0, "total_cost": 0.0})
        by_model[m]["requests"] += 1
        by_model[m]["total_latency_ms"] += t.total_latency_ms
        by_model[m]["total_cost"] += t.estimated_cost

        d = t.created_at.strftime("%Y-%m-%d")
        by_date.setdefault(d, {"requests": 0, "failed": 0})
        by_date[d]["requests"] += 1
        if t.final_outcome == "failure":
            by_date[d]["failed"] += 1
    for m, bucket in by_model.items():
        bucket["avg_latency_ms"] = round(bucket["total_latency_ms"] / bucket["requests"], 1)
        bucket["total_cost"] = round(bucket["total_cost"], 6)

    latest_report = report_summaries[-1] if report_summaries else None
    rag_evaluation = latest_report.get("rag_evaluation") if latest_report else None
    agent_evaluation = latest_report.get("agent_evaluation") if latest_report else None
    by_category = latest_report.get("by_category") if latest_report else None

    recent_traces = traces[:25]

    return render_template(
        "observability_dashboard.html",
        latency=lat, reliability=rel, usage=usage, cost=cost,
        cost_model_breakdown=cost_model_breakdown, cost_agent_breakdown=cost_agent_breakdown,
        cost_feature_breakdown=cost_feature_breakdown, latency_breakdown=latency_breakdown, calls=calls,
        guardrail_events=guardrail_events, injection_attempts=injection_attempts,
        unauthorized_attempts=unauthorized_attempts, eval_runs=eval_runs,
        report_summaries=report_summaries, recent_traces=recent_traces,
        by_model=by_model, by_date=sorted(by_date.items(), reverse=True)[:14],
        rag_evaluation=rag_evaluation, agent_evaluation=agent_evaluation,
        by_category=by_category, latest_report=latest_report,
    )


@observability_bp.route("/trace/<trace_id>")
@login_required
def view_trace(trace_id):
    trace = Trace.query.filter_by(trace_id=trace_id).first_or_404()
    steps = TraceStep.query.filter_by(trace_id=trace.id).order_by(TraceStep.seq).all()
    return render_template("trace_viewer.html", trace=trace, steps=steps)


@observability_bp.route("/api/summary")
@login_required
def api_summary():
    traces = Trace.query.filter_by(user_id=current_user.id).order_by(Trace.created_at.desc()).limit(500).all()
    return jsonify({
        "latency": latency_summary(traces),
        "reliability": reliability_summary(traces),
        "usage": usage_summary(traces),
        "cost": aggregate_cost(traces),
    })
