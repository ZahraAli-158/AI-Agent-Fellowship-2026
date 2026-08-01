"""
Experiment 2: With vs Without Critic — Section 30.

Compares report quality when the Critic's revision loop is active versus
when it is bypassed (auto-approved with no review), on a request known to
surface a real evidence gap (agent-frameworks topic includes a
low-confidence "reliability" evidence item on the first research task).

Usage:
    python -m evaluation.experiment_2_with_without_critic
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("LLM_MODE", "mock")

from app.graph.workflow import run_workflow

REQUEST = "Research the current open-source agent frameworks and recommend one for a small engineering team."


def _quality_signals(state) -> dict:
    report = state.get("final_report")
    md = report.to_markdown() if report else ""
    analysis = state.get("analysis")
    return {
        "known_gap_detected_by_analyst": bool(analysis and analysis.known_gaps),
        "revision_count": state.get("revision_count", 0),
        "critic_explicitly_flagged_a_problem": bool(state.get("critic_feedback") and state["critic_feedback"].problems_found),
        "conclusions_show_a_critic_driven_revision": bool(analysis and any("revision note" in c.lower() for c in analysis.conclusions)),
        "risks_section_mentions_evidence_gap": "confidence" in md.lower() or "gap" in md.lower() or "sparse" in md.lower(),
        "final_status": state.get("workflow_status"),
    }


def run():
    print("--- WITH Critic (normal operation, max_revisions=2) ---")
    with_critic_state = run_workflow(user_request=REQUEST, run_id="EXP2-with-critic", max_revisions=2)
    with_signals = _quality_signals(with_critic_state)
    print(json.dumps(with_signals, indent=2))

    print("\n--- WITHOUT Critic (max_revisions=0, so its rejection can never trigger a revision) ---")
    without_critic_state = run_workflow(user_request=REQUEST, run_id="EXP2-without-critic", max_revisions=0)
    without_signals = _quality_signals(without_critic_state)
    print(json.dumps(without_signals, indent=2))

    lines = [
        "# Experiment 2 — With vs Without Critic",
        "",
        f"Request: \"{REQUEST}\" (chosen because its first research task always surfaces a "
        "low-confidence 'reliability' evidence item, giving the Critic something real to catch).",
        "",
        "| Signal | With Critic (max_revisions=2) | Without Critic (max_revisions=0) |",
        "|---|---|---|",
        f"| Revision cycles used | {with_signals['revision_count']} | {without_signals['revision_count']} |",
        f"| Analyst independently detects the low-confidence gap | {with_signals['known_gap_detected_by_analyst']} | {without_signals['known_gap_detected_by_analyst']} |",
        f"| Critic explicitly names a problem in its feedback | {with_signals['critic_explicitly_flagged_a_problem']} | {without_signals['critic_explicitly_flagged_a_problem']} |",
        f"| **Conclusions show a critic-driven revision actually happened** | **{with_signals['conclusions_show_a_critic_driven_revision']}** | **{without_signals['conclusions_show_a_critic_driven_revision']}** |",
        f"| Final report's Risks section surfaces the gap | {with_signals['risks_section_mentions_evidence_gap']} | {without_signals['risks_section_mentions_evidence_gap']} |",
        f"| Final workflow status | {with_signals['final_status']} | {without_signals['final_status']} |",
        "",
        "## Interpretation",
        "",
        "The Analyst independently flags the low-confidence evidence gap in both conditions (it computes "
        "`known_gaps` directly from the evidence confidence distribution, with no dependency on the "
        "Critic) — so a naive 'does the gap get flagged at all' signal doesn't isolate the Critic's "
        "contribution. The row that does isolate it is whether the conclusions show a **critic-driven "
        "revision actually happened**: with the Critic able to act (`max_revisions=2`), it reviews the "
        "Analyst's first pass, flags the gap as an *unsupported-claims* problem, and forces one revision "
        "cycle whose output explicitly notes what was addressed. With `max_revisions=0`, the Critic node "
        "still runs and still produces the same `revision_requested` decision internally, but the routing "
        "logic (`decide_after_critic`) is forced to treat the cap as already reached, so the Analyst's "
        "un-revised first draft goes straight to the Writer with no record of a critic-driven correction. "
        "This is the concrete, measurable value one revision cycle buys.",
        "",
        "*(Note: `critic_explicitly_flagged_a_problem` looks reversed at first glance because it reflects "
        "the LAST recorded critic_feedback in each run — in the with-critic case, that's the critic's "
        "SECOND look, after the revision, where it now approves; in the without-critic case, it's the "
        "critic's only (rejected) look, whose rejection was simply never acted on.)*",
    ]
    with open("docs/experiment_2_with_without_critic.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\nWrote docs/experiment_2_with_without_critic.md")


if __name__ == "__main__":
    run()
