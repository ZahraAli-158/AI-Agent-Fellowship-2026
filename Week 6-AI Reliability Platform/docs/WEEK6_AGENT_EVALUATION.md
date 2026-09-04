# Week 6 §16 — Agent Evaluation

Implementation: `evaluation/evaluators/agent_eval.py`, wired into every
`evaluation/runner.py` run as `summary.agent_evaluation`.

## Scoping note (read this first)

The AI Workspace Platform's **Meeting Agent** (`app/services/agent_service.py`)
is a **single agent with multiple tools** — the model picks from
`create_task`, `list_tasks`, `update_task`, `complete_task`, `delete_task`,
`extract_meeting_notes`, `send_email_summary` within one conversational
turn. It is **not** a multi-agent system with handoffs between distinct
named agents (that pattern exists in the separate Week 4 MADIP project's
Supervisor/Research/Analyst/Critic/Writer graph, not here). §16 explicitly
scopes its multi-agent metrics to "for multi-agent systems" — this project
therefore reports them as `applicable: false` (see below) rather than
fabricating numbers for a pattern that doesn't exist in this codebase.

## Single-agent dimensions measured (agent-system-v3 results)

| Dimension | How it's measured | Result |
|---|---|---|
| **Intent understanding** | `eval_intent_understanding`: ambiguous requests (Category C) get a clarifying question; non-ambiguous ones don't get needlessly blocked | 100% (62/62) |
| **Tool selection** | `eval_tool_selection` (deterministic) | 100% (10/10 Category D cases) |
| **Argument generation** | `eval_tool_arguments` (deterministic) | 100% |
| **Planning** | `eval_planning`: for Category B cases that genuinely require tool sequencing/conditionals (an `expected_tool` is set), did the system act on the real logic instead of falling through to a generic stub? | 100% (v3; was 50% in `baseline_v1` — see `docs/WEEK6_ROOT_CAUSE_ANALYSIS.md` items B04/B07) |
| **Routing** | Single-agent system: "routing" here means tool routing, not agent-to-agent routing — see Tool selection above | 100% |
| **Handoff quality** | N/A — no agent-to-agent handoff exists in this system; see scoping note | not applicable |
| **State management** | `eval_state_management`: any stateful tool call reaches a terminal, non-error `final_state` | 100% |
| **Task completion** | Covered by the overall task-success gate — see `docs/WEEK6_TASK_SUCCESS_DEFINITION.md` | 100% |
| **Loop frequency** | Avg. tool calls per turn (`AgentLoopGuard`-bounded live, tracked per-case in the offline harness) | 0.419 tool calls/case avg (expected — most of the 62 cases are non-tool conversational/RAG/ambiguous requests; Category D+some B/A cases are the ones that call a tool at all) |
| **Recovery behavior** | `eval_recovery_behavior`: does the system ask for a valid value instead of silently using an invalid one on Category D missing/invalid-parameter cases (D05-D07)? | 100% (v3; was 67% in `baseline_v1` — see RCA items D06/D07) |

## Multi-agent metrics (§16, "for multi-agent systems also measure")

```json
{
  "applicable": false,
  "reason": "single agent, multiple tools — no agent-to-agent handoff exists in this codebase",
  "agent_routing_accuracy": null,
  "handoff_success_rate": null,
  "revision_count": null,
  "unnecessary_agent_calls": null
}
```

This is reported explicitly as `null`/`not applicable` rather than being
silently omitted, so it's clear the metric was considered and found
inapplicable, not forgotten.

## Live permission enforcement (a real fix made during this evaluation)

Building this evaluator surfaced a genuine gap: `app.guardrails.permissions`
(the L0–L4 tool risk classification) existed as infrastructure but was
**not actually wired into the live agent tool path** —
`app/services/agent_service.py`'s `delete_task` and `send_email_summary`
closures executed unconditionally the moment the model called them. This
has been fixed: both tools now call
`app.guardrails.permissions.authorize_tool_call` before executing, refusing
without an explicit `approved_tools` set threaded from the route
(`app/routes/agent_routes.py`). Verified end-to-end in
`tests/test_week6_agent_permissions.py` (4 tests: unapproved delete is
refused and the task survives; approved delete succeeds and the task is
gone; low-risk `create_task` never requires approval; unapproved email is
refused). This closes Security Review risk #4 for real, not just on paper
— see `docs/WEEK6_SECURITY_REVIEW.md`.
