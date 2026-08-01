"""
Execution Tracer — Requirement 15 (Section 23).

Records ONLY operational events (agent start/end, tool calls, handoffs,
revisions, errors, human approvals) — never private chain-of-thought
reasoning. Every helper here takes structured, already-decided facts
(who, what, when) and appends them to state["trace"]; it never receives
or logs raw model "thinking" text.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List


def _now() -> str:
    return time.strftime("%H:%M:%S")


def event(event_type: str, **fields: Any) -> Dict[str, Any]:
    """Builds one structured trace event. `event_type` is one of:
    agent_start, agent_end, tool_call, handoff, revision, error,
    human_approval, status_change.
    """
    return {"time": _now(), "type": event_type, **fields}


def agent_start(agent: str) -> Dict[str, Any]:
    return event("agent_start", agent=agent)


def agent_end(agent: str, duration_s: float | None = None) -> Dict[str, Any]:
    return event("agent_end", agent=agent, duration_s=duration_s)


def tool_call(agent: str, tool: str, success: bool, detail: str = "") -> Dict[str, Any]:
    return event("tool_call", agent=agent, tool=tool, success=success, detail=detail)


def handoff(from_agent: str, to_agent: str, summary: str = "") -> Dict[str, Any]:
    return event("handoff", from_agent=from_agent, to_agent=to_agent, summary=summary)


def revision(cycle: int, max_cycles: int, reason: str) -> Dict[str, Any]:
    return event("revision", cycle=cycle, max_cycles=max_cycles, reason=reason)


def error(agent: str, error_type: str, detail: str) -> Dict[str, Any]:
    return event("error", agent=agent, error_type=error_type, detail=detail)


def human_approval(checkpoint: str, decision: str) -> Dict[str, Any]:
    return event("human_approval", checkpoint=checkpoint, decision=decision)


def edited(checkpoint: str, fields_changed: List[str]) -> Dict[str, Any]:
    """Records that a human edited state at a checkpoint (Edit & Continue),
    and which fields were changed, without duplicating the full edited
    content into the Execution Log (that lives in the state itself /
    State Inspector)."""
    return event("edited", checkpoint=checkpoint, fields_changed=fields_changed)


def status_change(new_status: str) -> Dict[str, Any]:
    return event("status_change", status=new_status)


def summarize_run(run_id: str, trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Builds the Requirement 15 run summary from the raw trace list."""
    agents_invoked = sorted({e["agent"] for e in trace if e["type"] == "agent_start"})
    tools_called = [e for e in trace if e["type"] == "tool_call"]
    handoffs = [e for e in trace if e["type"] == "handoff"]
    revisions = [e for e in trace if e["type"] == "revision"]
    errors = [e for e in trace if e["type"] == "error"]
    approvals = [e for e in trace if e["type"] == "human_approval"]
    start_time = trace[0]["time"] if trace else None
    end_time = trace[-1]["time"] if trace else None
    return {
        "run_id": run_id,
        "agents_invoked": agents_invoked,
        "tools_called": len(tools_called),
        "handoffs": len(handoffs),
        "revision_cycles": len(revisions),
        "errors": len(errors),
        "human_approvals": len(approvals),
        "start_time": start_time,
        "end_time": end_time,
    }
