"""
Experiment 4: Shared Full Context vs Role-Specific Context — Section 30.

The current system already implements role-specific context (Requirement
13 / docs/context_management.md): each agent's LLM call payload is a
narrow, purpose-built subset of state, not the full workflow history. This
experiment measures WHAT that design choice actually saves, by
constructing the alternative ("shared full context" — dump the entire
WorkflowState into every agent's prompt) for the same real run and
comparing payload sizes directly.

Honesty note on scope: token usage and cost are measured directly (payload
size is a real, comparable number regardless of LLM mode). "Output
relevance" is NOT fabricated from mock-mode text, since the mock LLM is a
deterministic function of a few specific fields and would not actually
degrade with a larger prompt the way a real model can (context dilution /
the "lost in the middle" effect). That degradation is a well-documented
property of real LLMs, not something mock mode can honestly demonstrate —
this is stated plainly in the report rather than faked.

Usage:
    python -m evaluation.experiment_4_context_strategies
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("LLM_MODE", "mock")

from app.graph.workflow import run_workflow

REQUEST = "Compare three cloud platforms for deploying an AI SaaS application."
COST_PER_1K_TOKENS_USD = 0.0004  # conservative small-model input-token rate, for illustration only


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # ~4 chars/token is a standard rough estimate


def run():
    state = run_workflow(user_request=REQUEST, run_id="EXP4-context", max_revisions=2)

    # --- Role-specific context (what the system ACTUALLY sends the Analyst) ---
    evidence = state["evidence"]
    criteria = state["research_objective"].get("evaluation_criteria", [])
    role_specific_payload = json.dumps({
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "criteria": criteria,
    })

    # --- Shared full context (the alternative: dump everything) ---
    shared_full_payload = json.dumps({
        "user_request": state["user_request"],
        "clarifications": state["clarifications"],
        "research_objective": state["research_objective"],
        "task_plan": [t.model_dump(mode="json") for t in state["task_plan"]],
        "completed_tasks": state["completed_tasks"],
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "errors": state["errors"],
        "trace": state["trace"],  # every agent_start/tool_call/handoff event ever recorded
        "revision_count": state["revision_count"],
        "workflow_status": state["workflow_status"],
    })

    role_tokens = _approx_tokens(role_specific_payload)
    shared_tokens = _approx_tokens(shared_full_payload)
    reduction_pct = round(100 * (1 - role_tokens / shared_tokens), 1)

    print(f"Role-specific context: {len(role_specific_payload)} chars, ~{role_tokens} tokens")
    print(f"Shared full context:   {len(shared_full_payload)} chars, ~{shared_tokens} tokens")
    print(f"Reduction: {reduction_pct}%")

    lines = [
        "# Experiment 4 — Shared Full Context vs Role-Specific Context",
        "",
        f"Request: \"{REQUEST}\" — measuring what the Analyst's ACTUAL prompt payload "
        "(role-specific: filtered evidence + criteria) costs versus the alternative "
        "(shared full context: the entire WorkflowState, including full trace history).",
        "",
        "| Metric | Role-Specific Context (actual) | Shared Full Context (hypothetical) |",
        "|---|---|---|",
        f"| Payload size (chars) | {len(role_specific_payload)} | {len(shared_full_payload)} |",
        f"| Approx. tokens (~4 chars/token) | {role_tokens} | {shared_tokens} |",
        f"| Estimated input-token cost (USD, illustrative rate) | ${role_tokens / 1000 * COST_PER_1K_TOKENS_USD:.5f} | ${shared_tokens / 1000 * COST_PER_1K_TOKENS_USD:.5f} |",
        f"| **Token reduction from role-specific context** | — | **{reduction_pct}%** |",
        "",
        "## Output relevance — measured honestly, not fabricated",
        "",
        "This experiment does **not** report a measured 'output relevance' score for the shared-full-context "
        "condition, because mock mode's LLM responses are deterministic functions of a few specific input "
        "fields — feeding it a larger, noisier payload would not actually change its output the way a real "
        "model's output degrades with excess/irrelevant context (a well-documented behavior sometimes called "
        "context dilution or the 'lost in the middle' effect). Claiming a measured relevance drop here would "
        "be fabricating a number mock mode cannot honestly produce. The token-count difference above is real "
        "and directly measured; the relevance/quality argument for role-specific context rests on that "
        "documented LLM behavior plus the practical points in `docs/context_management.md` (agents cite "
        "evidence IDs instead of re-reading full text, aggregate summaries instead of full evidence dumps, "
        "etc.), not on a number this script invents.",
        "",
        "## Interpretation",
        "",
        f"For this run, role-specific context uses **{reduction_pct}% fewer tokens** than shared full "
        "context would, primarily because the full-context version carries the entire execution trace "
        "(every tool call, agent start/end, and handoff event) and task plan into every single agent call, "
        "none of which the Analyst actually needs to do its job. At scale (longer runs, more revision "
        "cycles, larger evidence stores), this gap grows roughly linearly with trace length, since "
        "role-specific context stays flat (bounded by evidence + criteria) while shared full context grows "
        "with every additional logged event.",
    ]
    with open("docs/experiment_4_context_strategies.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\nWrote docs/experiment_4_context_strategies.md")


if __name__ == "__main__":
    run()
