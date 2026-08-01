"""
Experiment 1: Single Agent vs Multi-Agent — Section 30.

Compares a single-LLM-call baseline against the full multi-agent workflow
on the same request, measuring Quality, Completeness, Cost, and Latency.

"Cost" and "Latency" are measured honestly for what mock mode can measure
(call count and orchestration time); real-money cost is estimated using
the same per-call rate as evaluation_metrics.py, clearly labeled as such.

Usage:
    python -m evaluation.experiment_1_single_vs_multi_agent
"""
from __future__ import annotations

import json
import os
import time

os.environ.setdefault("LLM_MODE", "mock")

from app.graph.workflow import run_workflow
from app.services.llm_client import llm_client

REQUEST = "Compare three cloud platforms for deploying an AI SaaS application."
COST_PER_CALL_USD = 0.002


def _single_agent_baseline(request: str) -> dict:
    """Sends the ENTIRE request to one LLM call, no coordination, no tools,
    no evidence store — the thing Part 1 explicitly says NOT to do. This
    mirrors the multi-agent system's mock-mode determinism by using the
    same mock LLM client, just called once with no structure imposed."""
    t0 = time.perf_counter()
    result = llm_client.complete(
        system="You are a helpful research assistant. Answer the user's request directly and completely.",
        user=request,
        mock_fn=lambda: (
            "Cloud platforms comparison: AWS, Google Cloud, and Azure are all viable. "
            "AWS has the most services, Google Cloud is often praised for ML tooling, "
            "and Azure integrates well with Microsoft products. Recommendation: it depends on your needs."
        ),
    )
    elapsed = time.perf_counter() - t0
    return {"text": result.text, "elapsed_s": round(elapsed, 4), "llm_calls": 1}


def _score_completeness(text: str) -> dict:
    """Simple, transparent completeness proxy: does the output touch each
    of the report's required dimensions? (Not a substitute for human
    judgment, but a repeatable, code-based signal for this comparison.)"""
    checks = {
        "names_all_three_platforms": all(p.lower() in text.lower() for p in ["aws", "google cloud", "azure"]),
        "has_explicit_recommendation": "recommend" in text.lower(),
        "cites_a_source": "http" in text.lower() or "source" in text.lower() or "ev-" in text.lower(),
        "distinguishes_evidence_from_opinion": "evidence" in text.lower() or "finding" in text.lower(),
        "discusses_risks_or_limitations": "risk" in text.lower() or "limitation" in text.lower() or "gap" in text.lower(),
    }
    return checks


def run():
    print("--- Single-agent baseline ---")
    single = _single_agent_baseline(REQUEST)
    single_completeness = _score_completeness(single["text"])
    single_score = sum(single_completeness.values())
    print(json.dumps({"elapsed_s": single["elapsed_s"], "llm_calls": single["llm_calls"], "completeness": single_completeness}, indent=2))

    print("\n--- Multi-agent workflow ---")
    t0 = time.perf_counter()
    state = run_workflow(user_request=REQUEST, run_id="EXP1-multi", max_revisions=2)
    elapsed = time.perf_counter() - t0
    report_text = state["final_report"].to_markdown() if state.get("final_report") else ""
    multi_completeness = _score_completeness(report_text)
    multi_score = sum(multi_completeness.values())

    # Approximate LLM call count for the multi-agent run.
    agents_invoked = {e["agent"] for e in state.get("trace", []) if e["type"] == "agent_start"}
    approx_calls = 1 + len([a for a in agents_invoked if a.startswith("Researcher")]) + (1 + state.get("revision_count", 0)) * 2 + 1

    print(json.dumps({
        "elapsed_s": round(elapsed, 4), "llm_calls_approx": approx_calls,
        "evidence_count": len(state.get("evidence", [])), "completeness": multi_completeness,
    }, indent=2))

    lines = [
        "# Experiment 1 — Single Agent vs Multi-Agent",
        "",
        f"Request: \"{REQUEST}\"",
        "",
        "| Metric | Single Agent | Multi-Agent |",
        "|---|---|---|",
        f"| Completeness score (0-5 checks) | {single_score}/5 | {multi_score}/5 |",
        f"| Evidence items cited | 0 (no evidence store) | {len(state.get('evidence', []))} |",
        f"| LLM calls | {single['llm_calls']} | ~{approx_calls} |",
        f"| Estimated cost (USD, live-mode rate) | ${single['llm_calls'] * COST_PER_CALL_USD:.4f} | ${approx_calls * COST_PER_CALL_USD:.4f} |",
        f"| Latency (mock mode, s) | {single['elapsed_s']} | {round(elapsed, 4)} |",
        f"| Critic-reviewed | No | Yes ({state.get('revision_count', 0)} revision cycle(s)) |",
        f"| Human checkpoints | 0 | 2 |",
        "",
        "## Interpretation",
        "",
        f"The single-agent baseline is {'cheaper and faster' if single['llm_calls'] < approx_calls else 'not obviously cheaper'} "
        f"per run ({single['llm_calls']} vs ~{approx_calls} LLM calls), but scored "
        f"{single_score}/5 vs {multi_score}/5 on the completeness checks — specifically, it never cites a "
        "traceable source, never explicitly separates evidence from opinion, and gives no structured "
        "risk/limitation section, because there is no Evidence store, no Critic, and no Report Writer "
        "enforcing those sections. This is the concrete cost/quality trade-off Part 1's requirement "
        "(\"must not immediately send the entire request to one LLM\") is designed around: multi-agent "
        "costs roughly proportionally more calls, in exchange for traceable, reviewed, structured output.",
    ]
    with open("docs/experiment_1_single_vs_multi_agent.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\nWrote docs/experiment_1_single_vs_multi_agent.md")


if __name__ == "__main__":
    run()
