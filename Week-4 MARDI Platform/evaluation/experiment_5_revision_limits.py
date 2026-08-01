"""
Experiment 5: Different Revision Limits (0, 1, 2) — Section 30.

Runs the same request with max_revisions set to 0, 1, and 2, measuring
the trade-off between output quality (whether the evidence gap gets
explicitly addressed) and cost (extra Analyst+Critic call pairs actually
used per revision cycle).

Usage:
    python -m evaluation.experiment_5_revision_limits
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("LLM_MODE", "mock")

from app.graph.workflow import run_workflow

REQUEST = "Research the current open-source agent frameworks and recommend one for a small engineering team."
COST_PER_CALL_USD = 0.002


def run():
    rows = []
    for limit in (0, 1, 2):
        state = run_workflow(user_request=REQUEST, run_id=f"EXP5-max{limit}", max_revisions=limit)
        analysis = state.get("analysis")
        report = state.get("final_report")

        revision_cycles_used = state.get("revision_count", 0)
        extra_calls = revision_cycles_used * 2  # one extra Analyst call + one extra Critic call per cycle
        addressed = bool(analysis and any("revision note" in c.lower() for c in analysis.conclusions))

        rows.append({
            "max_revisions": limit,
            "revision_cycles_used": revision_cycles_used,
            "gap_explicitly_addressed_in_revision": addressed,
            "risks_section_present_and_nonempty": bool(report and len(report.risks_and_limitations) > 20),
            "extra_llm_calls_vs_zero_revisions": extra_calls,
            "estimated_extra_cost_usd": round(extra_calls * COST_PER_CALL_USD, 4),
            "final_status": state.get("workflow_status"),
        })
        print(json.dumps(rows[-1], indent=2))

    lines = [
        "# Experiment 5 — Different Revision Limits (0, 1, 2)",
        "",
        f"Request: \"{REQUEST}\" (same evidence-gap-triggering request used in Experiment 2, run three times "
        "with `max_revisions` set to 0, 1, and 2).",
        "",
        "| max_revisions | Revision cycles actually used | Gap explicitly addressed | Extra LLM calls vs. 0 | Est. extra cost (USD) | Final status |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['max_revisions']} | {r['revision_cycles_used']} | {r['gap_explicitly_addressed_in_revision']} "
            f"| +{r['extra_llm_calls_vs_zero_revisions']} | ${r['estimated_extra_cost_usd']:.4f} | {r['final_status']} |"
        )

    lines += [
        "",
        "## Interpretation",
        "",
        "With `max_revisions=0`, the Critic's rejection is never actionable — the workflow completes on the "
        "Analyst's first pass regardless of what the Critic finds, at the lowest cost. With `max_revisions=1` "
        "or higher, the single evidence gap this request always surfaces gets caught and explicitly addressed "
        "in exactly one revision cycle — going from 1 to 2 does not buy anything further for THIS request, "
        "because the mock Critic only ever asks for one concrete fix before approving (a deliberate design "
        "choice so the quality-control loop is demonstrably bounded, per Requirement 10). In a live-LLM "
        "deployment where the Critic might reasonably ask for more than one round of changes on harder "
        "requests, the marginal cost of raising the cap from 1 to 2 is exactly one more Analyst+Critic call "
        "pair (~2 calls), spent only if actually needed — the cap is a ceiling, not a fixed cost.",
    ]
    with open("docs/experiment_5_revision_limits.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\nWrote docs/experiment_5_revision_limits.md")


if __name__ == "__main__":
    run()
