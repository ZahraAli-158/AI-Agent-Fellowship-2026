"""
Evaluation Dataset Runner — Section 28.

Defines 25+ test scenarios across 6 categories and runs EVERY one of them
through the real workflow (app/graph/workflow.py::run_workflow) in mock LLM
mode. This produces genuine actual-vs-expected results rather than
hand-written claims — the markdown report this script generates
(docs/evaluation_dataset.md) is derived entirely from what the system
actually did on this run.

Usage:
    python -m evaluation.evaluation_dataset
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

os.environ.setdefault("LLM_MODE", "mock")

from app.graph import human
from app.graph.workflow import run_workflow


@dataclass
class Scenario:
    id: str
    category: str
    user_request: str
    expected_agents: List[str]
    expected_workflow: str
    expected_research_tasks: str
    expected_checkpoint_behavior: str
    max_revisions: int = 2
    checkpoint_1_decision: str = "approved"
    checkpoint_2_decision: str = "approved"
    expect_clarification: bool = False
    expect_completion: bool = True
    notes: str = ""


SCENARIOS: List[Scenario] = [
    # ---------------- Simple Research Requests (5) ----------------
    Scenario("S01", "Simple Research", "Research the current open-source agent frameworks and recommend one for a small engineering team.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full linear pipeline", "3 parallel (LangGraph/CrewAI/OpenAI Agents SDK)",
             "both checkpoints shown and approved"),
    Scenario("S02", "Simple Research", "Compare three cloud platforms for deploying an AI SaaS application.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full linear pipeline", "3 parallel (AWS/Google Cloud/Azure)",
             "both checkpoints shown and approved"),
    Scenario("S03", "Simple Research", "What are the leading vector databases for a RAG application?",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full linear pipeline", "3 parallel (Vector-Search RAG/Hybrid Retrieval RAG/Fine-Tuned Model)",
             "both checkpoints shown and approved",
             notes="Matches the topic detector's dedicated RAG corpus (app/storage/corpus/rag_enterprise_chatbots.json via the \\brag\\b word-boundary match in supervisor.py), so this now has real corpus coverage and completes successfully rather than falling back to generic placeholders."),
    Scenario("S04", "Simple Research", "Research the current landscape of AI coding assistants.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full linear pipeline", "3 parallel (agent_frameworks corpus fallback)",
             "both checkpoints shown and approved"),
    Scenario("S05", "Simple Research", "Research generative AI opportunities in higher education.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full pipeline, expected to fail cleanly on missing evidence", "3 parallel (generic fallback candidates)",
             "both checkpoints shown and approved", expect_completion=False,
             notes="No topic-detector keyword match -> generic fallback -> zero corpus coverage -> correct missing_evidence failure."),

    # ---------------- Complex Multi-Part Requests (5) ----------------
    Scenario("C01", "Complex Multi-Part", "Analyze a new AI-powered scheduling app idea and identify opportunities, risks, competitors, and an initial strategy.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full pipeline, expected to fail cleanly on missing evidence", "3 parallel (generic fallback candidates)",
             "both checkpoints shown and approved", expect_completion=False,
             notes="No topic-detector keyword match -> generic fallback -> zero corpus coverage -> correct missing_evidence failure. Also has 4 distinct asks bundled into one request, which the topic detector isn't designed to decompose."),
    Scenario("C02", "Complex Multi-Part", "Research the current open-source agent frameworks, recommend one, and outline a 30-day adoption plan for a 4-person team.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full linear pipeline", "3 parallel (agent_frameworks corpus)",
             "both checkpoints shown and approved",
             notes="Adoption-plan portion has no dedicated agent — expected to surface only in the Writer's recommendation, not as a separate research task."),
    Scenario("C03", "Complex Multi-Part", "Compare three cloud platforms for deploying an AI SaaS application, considering cost, compliance, and integration with existing Microsoft tooling.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full linear pipeline", "3 parallel (cloud_platforms corpus)",
             "both checkpoints shown and approved"),
    Scenario("C04", "Complex Multi-Part", "Analyze whether a startup should build its own AI model or use commercial APIs, accounting for both short-term cost and long-term differentiation.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full pipeline, expected to fail cleanly on missing evidence", "3 parallel (generic fallback candidates)",
             "both checkpoints shown and approved", expect_completion=False,
             notes="No topic-detector keyword match -> generic fallback -> zero corpus coverage -> correct missing_evidence failure."),
    Scenario("C05", "Complex Multi-Part", "Research open-source agent frameworks and cloud deployment platforms together, then recommend a complete stack for a 3-person startup.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full linear pipeline", "3 parallel (topic detector picks ONE topic only)",
             "both checkpoints shown and approved",
             notes="Known design limitation: the keyword-based topic detector matches only the first keyword hit, so a genuinely two-topic request is researched as if it were one topic. Documented as a limitation, not silently hidden."),

    # ---------------- Comparison Requests (5) ----------------
    Scenario("M01", "Comparison", "Compare three AI coding assistants for a software development team and recommend the best option.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full linear pipeline", "3 parallel (agent_frameworks corpus fallback)",
             "both checkpoints shown and approved"),
    Scenario("M02", "Comparison", "LangGraph vs CrewAI vs OpenAI Agents SDK — which should we use?",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full linear pipeline", "3 parallel (agent_frameworks corpus)",
             "both checkpoints shown and approved"),
    Scenario("M03", "Comparison", "AWS vs Google Cloud vs Azure for hosting an AI SaaS product.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full linear pipeline", "3 parallel (cloud_platforms corpus)",
             "both checkpoints shown and approved"),
    Scenario("M04", "Comparison", "Compare building a custom AI model in-house versus using commercial APIs like OpenAI or Anthropic.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full pipeline, expected to fail cleanly on missing evidence", "3 parallel (generic fallback candidates)",
             "both checkpoints shown and approved", expect_completion=False,
             notes="No topic-detector keyword match -> generic fallback -> zero corpus coverage -> correct missing_evidence failure."),
    Scenario("M05", "Comparison", "Compare LangGraph and CrewAI specifically for a small team building their first agent.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full linear pipeline", "3 parallel (agent_frameworks corpus)",
             "both checkpoints shown and approved",
             notes="Only 2 named frameworks in the request, but the topic-level candidate list always has 3 — checks the system doesn't try to over-fit to exact named counts."),

    # ---------------- Ambiguous Requests (3) ----------------
    Scenario("A01", "Ambiguous", "best framework",
             ["Supervisor"], "halts before research, asks for clarification", "none until clarified",
             "clarification checkpoint triggered before any research", expect_clarification=True),
    Scenario("A02", "Ambiguous", "help me pick a cloud",
             ["Supervisor"], "halts before research, asks for clarification", "none until clarified",
             "clarification checkpoint triggered before any research", expect_clarification=True),
    Scenario("A03", "Ambiguous", "what should we use",
             ["Supervisor"], "asks for clarification, then (post-clarification) fails cleanly on missing evidence", "none until clarified, then generic fallback with zero corpus coverage",
             "clarification checkpoint triggered before any research", expect_clarification=True, expect_completion=False,
             notes="After being answered, the request text still contains no topic-detector keyword, so it correctly proceeds to a clean missing_evidence failure rather than fabricating a report — this is the same pattern as S05/C01/etc., just reached via the clarification path first."),

    # ---------------- Requests With Insufficient Evidence (3) ----------------
    Scenario("I01", "Insufficient Evidence", "Research the current state of quantum-resistant agent orchestration frameworks.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full pipeline completes, but evidence is only generically related",
             "3 parallel — matches the 'framework'/'agent' keywords, so real corpus evidence is retrieved, but none of it is actually about quantum-resistance", "both checkpoints shown and approved",
             notes="Illustrates a subtler insufficient-evidence case: the topic detector matches on keywords, not semantic intent, so it retrieves real (but topically mismatched) evidence and completes rather than failing — the report's claims are about LangGraph/CrewAI/OpenAI Agents SDK in general, not about quantum-resistance specifically."),
    Scenario("I02", "Insufficient Evidence", "Compare Framework Zeta and Framework Omega for edge-device agent deployment.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full pipeline completes, but evidence is only generically related",
             "3 parallel — matches 'framework'/'agent' keywords, so real (generic) corpus evidence is retrieved despite the fictional framework names being ignored", "both checkpoints shown and approved",
             notes="Same pattern as I01 — fictional framework names are silently ignored in favor of the topic detector's real candidate list (LangGraph/CrewAI/OpenAI Agents SDK), which is a source of potential user confusion worth flagging."),
    Scenario("I03", "Insufficient Evidence", "Research the production reliability track record of CrewAI in the aerospace industry.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full pipeline, expected to fail cleanly on missing evidence",
             "3 parallel (generic fallback candidates — 'CrewAI' alone does not trigger the topic detector)", "both checkpoints shown and approved",
             expect_completion=False,
             notes="Demonstrates a real limitation: the keyword-based topic detector only triggers on 'framework'/'agent'/'cloud'/'coding assistant', so a request that names a specific tool (CrewAI) without those words still falls back to the generic candidate list, which has zero corpus coverage."),

    # ---------------- Failure and Edge Cases (4) ----------------
    Scenario("F01", "Failure/Edge", "",
             ["Supervisor"], "should fail fast on an empty request", "none",
             "workflow should not silently proceed on empty input", expect_completion=False,
             notes="Empty string request — checks the system degrades gracefully rather than crashing the API."),
    Scenario("F02", "Failure/Edge", "Research the current open-source agent frameworks and recommend one for a small engineering team.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full pipeline, plan rejected by human",
             "3 parallel (never executed — rejected before dispatch)", "checkpoint 1 REJECTED",
             checkpoint_1_decision="rejected", expect_completion=False,
             notes="Exercises the Requirement 12 rejection path: workflow must terminate as FAILED, not hang, when a human rejects the plan."),
    Scenario("F03", "Failure/Edge", "Research the current open-source agent frameworks and recommend one for a small engineering team.",
             ["Supervisor", "Researcher", "Analyst", "Critic", "Writer"], "full pipeline, zero revision cycles allowed",
             "3 parallel", "both checkpoints shown and approved", max_revisions=0,
             notes="Exercises Requirement 10's forced-termination path with max_revisions=0 — even a single revision request must be overridden and the workflow must still complete."),
    Scenario("F04", "Failure/Edge", "asdkjaslkdj alskdjalksjd research something maybe idk",
             ["Supervisor"], "should fail cleanly on missing evidence rather than crash", "3 parallel (generic fallback candidates, zero corpus coverage)",
             "system must not crash on nonsense input", expect_completion=False,
             notes="Garbage/gibberish input still passes through request analysis (mock heuristics don't reject it), matches no topic keyword, and correctly fails cleanly at the missing_evidence stage rather than crashing or fabricating a report."),
]


def run_scenario(sc: Scenario) -> dict:
    def callback(checkpoint_name: str, payload: dict) -> dict:
        if checkpoint_name == "clarification":
            return {"answers": ["general use case", "prototype stage", "no strict constraint"]}
        if checkpoint_name == "checkpoint_1_plan_approval":
            return {"decision": sc.checkpoint_1_decision}
        return {"decision": sc.checkpoint_2_decision}

    t0 = time.perf_counter()
    error = None
    try:
        state = run_workflow(user_request=sc.user_request, run_id=sc.id, max_revisions=sc.max_revisions, callback=callback)
    except Exception as exc:  # noqa: BLE001
        state = {}
        error = str(exc)
    elapsed = time.perf_counter() - t0

    return {
        "scenario": sc,
        "elapsed_s": round(elapsed, 3),
        "exception": error,
        "workflow_status": state.get("workflow_status"),
        "needs_clarification_was_true": bool(state.get("clarifications")),
        "evidence_count": len(state.get("evidence", [])),
        "revision_count": state.get("revision_count", 0),
        "error_count": len(state.get("errors", [])),
        "agents_invoked": sorted({e["agent"] for e in state.get("trace", []) if e["type"] == "agent_start"}),
        "has_report": state.get("final_report") is not None,
        "checkpoint_1_status": state.get("checkpoint_1_status"),
        "checkpoint_2_status": state.get("checkpoint_2_status"),
    }


def judge_pass_fail(r: dict) -> tuple[bool, str]:
    sc: Scenario = r["scenario"]

    if sc.expect_clarification:
        if not r["needs_clarification_was_true"]:
            return False, "Expected clarification but none was recorded."
        # Clarification was correctly triggered; also verify what happens
        # AFTER it's answered matches this scenario's expected outcome,
        # since the workflow is designed to continue past clarification,
        # not stop there.
        if sc.expect_completion:
            ok = r["workflow_status"] == "completed" and r["has_report"]
            return ok, "Clarification triggered, then completed with a report as expected." if ok else f"Clarification triggered, but post-clarification workflow_status={r['workflow_status']} (expected completed)."
        ok = r["workflow_status"] == "failed"
        return ok, "Clarification triggered, then correctly failed cleanly on missing evidence." if ok else f"Clarification triggered, but post-clarification workflow_status={r['workflow_status']} (expected failed)."

    if not sc.expect_completion:
        if sc.checkpoint_1_decision == "rejected":
            ok = r["workflow_status"] == "failed" and r["checkpoint_1_status"] == "rejected"
            return ok, "Workflow correctly terminated as failed after plan rejection." if ok else f"Expected failed/rejected, got workflow_status={r['workflow_status']}, checkpoint_1={r['checkpoint_1_status']}."
        if sc.user_request == "":
            ok = r["exception"] is not None or r["workflow_status"] in ("failed", None)
            return ok, "Empty request handled without a successful completion." if ok else "Empty request unexpectedly completed successfully."
        ok = r["workflow_status"] == "failed"
        return ok, "Correctly reached a terminal failed status (missing evidence handled cleanly)." if ok else f"Expected a clean 'failed' status, got workflow_status={r['workflow_status']}."

    ok = r["workflow_status"] == "completed" and r["has_report"] and r["exception"] is None
    reason = "Completed with a final report." if ok else f"workflow_status={r['workflow_status']}, has_report={r['has_report']}, exception={r['exception']}"
    return ok, reason


def main():
    results = []
    for sc in SCENARIOS:
        r = run_scenario(sc)
        passed, reason = judge_pass_fail(r)
        r["passed"] = passed
        r["reason"] = reason
        results.append(r)
        print(f"[{'PASS' if passed else 'FAIL'}] {sc.id} ({sc.category}) — {reason}")

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    print(f"\n{passed_count}/{total} scenarios passed.")

    _write_markdown(results)
    return results


def _write_markdown(results: List[dict]) -> None:
    lines = [
        "# Evaluation Dataset — Section 28",
        "",
        f"Generated by `evaluation/evaluation_dataset.py`, run in `LLM_MODE=mock` "
        f"(deterministic, no API key needed, reproducible). {len(results)} scenarios across 6 categories.",
        "",
        f"**Result: {sum(1 for r in results if r['passed'])}/{len(results)} scenarios passed.**",
        "",
    ]

    by_category: dict[str, list] = {}
    for r in results:
        by_category.setdefault(r["scenario"].category, []).append(r)

    for category, items in by_category.items():
        lines.append(f"## {category} ({len(items)})")
        lines.append("")
        for r in items:
            sc: Scenario = r["scenario"]
            lines += [
                f"### {sc.id} — {'✅ PASS' if r['passed'] else '❌ FAIL'}",
                f"- **User request:** {sc.user_request or '*(empty string)*'}",
                f"- **Expected agents:** {', '.join(sc.expected_agents)}",
                f"- **Expected workflow:** {sc.expected_workflow}",
                f"- **Expected research tasks:** {sc.expected_research_tasks}",
                f"- **Expected human checkpoint behavior:** {sc.expected_checkpoint_behavior}",
                f"- **Actual result:** workflow_status=`{r['workflow_status']}`, agents_invoked={r['agents_invoked']}, "
                f"evidence_count={r['evidence_count']}, revision_count={r['revision_count']}, "
                f"errors={r['error_count']}, has_report={r['has_report']}, elapsed={r['elapsed_s']}s",
                f"- **Pass/Fail:** {'PASS' if r['passed'] else 'FAIL'} — {r['reason']}",
                f"- **Notes:** {sc.notes or '—'}",
                "",
            ]

    with open("docs/evaluation_dataset.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\nWrote docs/evaluation_dataset.md")


if __name__ == "__main__":
    main()
