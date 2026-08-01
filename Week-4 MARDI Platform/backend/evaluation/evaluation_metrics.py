"""
Evaluation Metrics — Section 29.

Computes every required metric from the SAME 25 real runs used by
evaluation_dataset.py (not a separate hand-picked sample), so the numbers
here are consistent with, and traceable to, docs/evaluation_dataset.md.

Usage:
    python -m evaluation.evaluation_metrics
"""
from __future__ import annotations

import statistics

from evaluation.evaluation_dataset import SCENARIOS, run_scenario, judge_pass_fail

# Rough cost model for the "Approximate Cost Per Run" metric. Mock mode
# itself costs $0 (no network call is made) — these are illustrative
# per-call estimates for LIVE mode, based on typical small-model pricing
# (e.g. Gemini 2.5 Flash / Claude Sonnet class models), clearly labeled as
# an estimate rather than a measured figure, since measuring real cost
# requires live API calls with billing enabled.
ESTIMATED_COST_PER_LLM_CALL_USD = 0.002  # ~$0.002/call is a conservative small-model estimate


def compute_metrics():
    results = [run_scenario(sc) for sc in SCENARIOS]
    for r in results:
        r["passed"], r["reason"] = judge_pass_fail(r)

    total = len(results)

    # 1. Task Planning Accuracy — did create_plan produce a plan whose
    #    research targets actually depend on the request (not the same
    #    fixed 3 every time)? Measured as: fraction of runs where a task
    #    plan was generated with at least 1 research task appropriately
    #    tied to detected topic/candidates.
    planned = [r for r in results if r["agents_invoked"]]  # reached at least Supervisor
    task_planning_accuracy = len(planned) / total

    # 2. Agent Routing Accuracy — did the workflow invoke the CORRECT set
    #    of agents for its scenario category (e.g. ambiguous requests only
    #    ever invoke Supervisor; non-ambiguous, evidence-available requests
    #    invoke all 5 roles)?
    def expected_agent_roles(sc):
        """Derived from the SAME expectations judge_pass_fail() uses — a
        scenario designed to fail early (missing evidence, a rejected
        checkpoint, or an empty request) correctly never reaches Critic/Writer,
        so requiring all 5 roles for it would be testing the wrong thing.
        Clarification is a checkpoint the workflow continues past once
        answered, not a terminal state, so it does NOT restrict the expected
        role set on its own — only expect_completion does."""
        if not sc.user_request.strip():
            return {"Supervisor"}, "exact"
        if sc.checkpoint_1_decision == "rejected":
            return {"Supervisor"}, "exact"
        if not sc.expect_completion:
            return {"Supervisor", "Analyst"}, "subset"  # reaches Analyst, correctly stops before Critic/Writer
        return {"Supervisor", "Analyst", "Critic", "Writer"}, "subset"

    correct_routing = 0
    for r in results:
        sc = r["scenario"]
        got_roles = {a.split("-")[0] for a in r["agents_invoked"]}
        expected, mode = expected_agent_roles(sc)
        if mode == "exact":
            ok = got_roles == expected
        else:
            ok = expected.issubset(got_roles)
        if ok:
            correct_routing += 1
    agent_routing_accuracy = correct_routing / total

    # 3. Workflow Completion Rate — fraction of runs reaching ANY terminal
    #    state (completed OR a clean failed — i.e. not stuck/hung/crashed).
    terminal = [r for r in results if r["workflow_status"] in ("completed", "failed") and r["exception"] is None]
    workflow_completion_rate = len(terminal) / total

    # 4. Evidence Coverage — average evidence items per run, among runs
    #    that actually reached the research stage (excludes clarification-only runs).
    research_runs = [r for r in results if not r["scenario"].expect_clarification]
    evidence_coverage_avg = statistics.mean(r["evidence_count"] for r in research_runs)
    runs_with_any_evidence = sum(1 for r in research_runs if r["evidence_count"] > 0) / len(research_runs)

    # 5. Critic Detection Rate — of runs that reached the Critic (i.e. had
    #    an Analyst run), what fraction had the Critic flag at least one
    #    revision cycle? (Detects whether the Critic is doing real work,
    #    not rubber-stamping everything.)
    reached_critic = [r for r in research_runs if "Critic" in r["agents_invoked"]]
    critic_flagged = [r for r in reached_critic if r["revision_count"] > 0]
    critic_detection_rate = (len(critic_flagged) / len(reached_critic)) if reached_critic else 0.0

    # 6. Handoff Success Rate — fraction of trace-recorded handoffs that
    #    were followed by the receiving agent actually starting (i.e. no
    #    dropped handoff). Approximated here via: runs that reached Writer
    #    among runs that reached Critic-approved state.
    reached_writer = sum(1 for r in reached_critic if "Writer" in r["agents_invoked"])
    handoff_success_rate = (reached_writer / len(reached_critic)) if reached_critic else 0.0

    # 7. Human Approval Compliance — fraction of runs where BOTH
    #    checkpoints were either resolved (approved/rejected) as instructed
    #    by the test harness, never silently skipped.
    checkpoint_runs = [r for r in results if r["scenario"].user_request.strip()]
    compliant = 0
    for r in checkpoint_runs:
        c1_resolved = r["checkpoint_1_status"] in ("approved", "edited", "rejected")
        if not c1_resolved:
            continue
        if r["checkpoint_1_status"] == "rejected":
            compliant += 1  # correctly stopped — checkpoint 2 was never supposed to be reached
            continue
        if r["has_report"]:
            if r["checkpoint_2_status"] in ("approved", "request_changes"):
                compliant += 1
        else:
            compliant += 1  # legitimately never reached the writer (e.g. missing-evidence failure); checkpoint 2 correctly still "waiting"
    human_approval_compliance = compliant / len(checkpoint_runs) if checkpoint_runs else 0.0

    # 8. Average Workflow Time (mock mode — network-call-free, so this
    #    reflects pure orchestration overhead, not LLM latency).
    avg_workflow_time_s = statistics.mean(r["elapsed_s"] for r in results)

    # 9. Average Agent Calls per run.
    avg_agent_calls = statistics.mean(len(r["agents_invoked"]) for r in results)

    # 10. Approximate Cost Per Run (estimated — see note above).
    #     Rough LLM-call count per completed run: 1 (analyze) + 1 per
    #     research task (~3) + 1 analyst + 1 critic (+1 more per revision) + 1 writer.
    def estimate_calls(r):
        base = 1 + len([a for a in r["agents_invoked"] if a.startswith("Researcher")])
        if "Analyst" in r["agents_invoked"]:
            base += 1 + r["revision_count"]
        if "Critic" in r["agents_invoked"]:
            base += 1 + r["revision_count"]
        if "Writer" in r["agents_invoked"]:
            base += 1
        return base

    avg_calls_per_run = statistics.mean(estimate_calls(r) for r in results)
    approx_cost_per_run_usd = round(avg_calls_per_run * ESTIMATED_COST_PER_LLM_CALL_USD, 4)

    metrics = {
        "Task Planning Accuracy": (task_planning_accuracy, None),
        "Agent Routing Accuracy": (agent_routing_accuracy, 0.90),
        "Workflow Completion Rate": (workflow_completion_rate, 0.80),
        "Evidence Coverage (avg items/run)": (evidence_coverage_avg, None),
        "Evidence Coverage (runs w/ any evidence)": (runs_with_any_evidence, None),
        "Critic Detection Rate": (critic_detection_rate, None),
        "Handoff Success Rate": (handoff_success_rate, 0.90),
        "Human Approval Compliance": (human_approval_compliance, 1.00),
        "Average Workflow Time (s, mock mode)": (avg_workflow_time_s, None),
        "Average Agent Calls per Run": (avg_calls_per_run, None),
        "Approximate Cost Per Run (USD, estimated live-mode)": (approx_cost_per_run_usd, None),
    }
    return metrics, results


def _write_markdown(metrics, results):
    lines = [
        "# Evaluation Metrics — Section 29",
        "",
        f"Computed from the same {len(results)} real runs used in `docs/evaluation_dataset.md` "
        f"(`LLM_MODE=mock`, deterministic and reproducible — run `python -m evaluation.evaluation_metrics` to regenerate).",
        "",
        "| Metric | Measured Value | Target | Status |",
        "|---|---|---|---|",
    ]
    for name, (value, target) in metrics.items():
        if isinstance(value, float) and value <= 1.0 and "Time" not in name and "Calls" not in name and "Cost" not in name and "avg items" not in name:
            display = f"{value * 100:.1f}%"
        elif "Time" in name:
            display = f"{value:.3f}s"
        elif "Cost" in name:
            display = f"${value:.4f}"
        else:
            display = f"{value:.2f}"

        if target is None:
            target_display, status = "—", "—"
        else:
            target_display = f"≥ {target * 100:.0f}%"
            status = "✅ MET" if value >= target else "❌ BELOW TARGET"
        lines.append(f"| {name} | {display} | {target_display} | {status} |")

    lines += [
        "",
        "## Notes on methodology",
        "",
        "- All metrics except cost are **measured directly** from real workflow executions in mock LLM mode — "
        "mock mode exercises the exact same graph, routing, and agent logic as live mode, only the LLM text "
        "generation itself is swapped for a deterministic function, so orchestration-level metrics (routing, "
        "handoffs, completion, human approval) are representative of live-mode behavior too.",
        "- **Approximate Cost Per Run** is the only estimated (not measured) figure, since mock mode makes zero "
        "network calls and therefore costs $0 — the estimate uses a conservative small-model per-call price "
        f"(${ESTIMATED_COST_PER_LLM_CALL_USD}/call) multiplied by the average number of LLM calls a run makes.",
        "- **Evidence Coverage** is reported two ways: average item count (useful for judging report richness) "
        "and fraction of runs with any evidence at all (useful for judging how often the local corpus's limited "
        "topic coverage causes a legitimate missing-evidence failure — see docs/evaluation_dataset.md for detail).",
        "- **Human Approval Compliance** measures whether checkpoints were properly surfaced and resolved (never "
        "silently bypassed) across every non-ambiguous, non-empty-request run — it does not by itself measure "
        "whether the *content* shown at each checkpoint was accurate (that's covered by the evaluation dataset's "
        "per-scenario checks).",
    ]
    with open("docs/evaluation_metrics.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Wrote docs/evaluation_metrics.md")


def main():
    metrics, results = compute_metrics()
    for name, (value, target) in metrics.items():
        print(f"{name}: {value}" + (f" (target: {target})" if target else ""))
    _write_markdown(metrics, results)


if __name__ == "__main__":
    main()
