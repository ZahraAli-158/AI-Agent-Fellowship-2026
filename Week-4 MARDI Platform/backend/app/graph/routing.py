"""
Routing — conditional edges for the LangGraph workflow.

This is where three of the trickiest requirements live:
  - Requirement 11 (Parallel Execution): `dispatch_research` fans out one
    Send() per ready research task, so they execute concurrently.
  - Requirement 10 (Quality-Control Loop): `route_after_critic_decision`
    enforces the max-revision cap so the loop ALWAYS terminates, even if
    the Critic keeps requesting revisions.
  - Requirement 2 (Clarification): `route_after_request_analysis` sends
    the workflow to the clarification checkpoint before any research
    (and therefore any cost) is incurred.
"""
from __future__ import annotations

from typing import List, Union

from langgraph.graph import END
from langgraph.types import Send

from app.graph.state import WorkflowState, WorkflowStatus
from app.schemas.tasks import AgentRole, TaskStatus


def route_after_request_analysis(state: WorkflowState) -> str:
    if state.get("workflow_status") == WorkflowStatus.FAILED:
        return END
    return "clarify" if state.get("needs_clarification") else "create_plan"


def route_after_clarification(state: WorkflowState) -> str:
    return "create_plan"


def dispatch_research(state: WorkflowState) -> Union[str, List[Send]]:
    """Fans research tasks whose dependencies are satisfied out to parallel
    `researcher` node invocations (Requirement 11). LangGraph will wait for
    ALL of these Sends to finish before the shared `analyst` downstream node
    (which every Send implicitly targets) runs — a fan-out/fan-in join.
    """
    if state.get("workflow_status") == WorkflowStatus.FAILED:
        return END

    completed = set(state.get("completed_tasks", []))
    sends: List[Send] = []
    for task in state["task_plan"]:
        is_researcher = task.assigned_agent == AgentRole.RESEARCHER.value or task.assigned_agent == AgentRole.RESEARCHER
        if is_researcher and task.id not in completed and task.is_ready(list(completed)):
            sends.append(Send("researcher", {"task": task}))

    return sends if sends else "analyst"


def route_after_analysis(state: WorkflowState) -> str:
    """Guards against the Analyst's missing_evidence failure path crashing
    the Critic node (Requirement 14: Missing Evidence handling)."""
    return "critic" if state.get("analysis") is not None else END


def route_after_critic(state: WorkflowState) -> str:
    """Guards against the Critic's model_api_failure / invalid_structured_output
    failure paths crashing `decide_after_critic`, which otherwise assumes
    `critic_feedback` is always populated. Without this guard, a Critic
    failure left the graph stuck (state never reached COMPLETED or FAILED) —
    this mirrors the same short-circuit-to-END pattern already used by
    `route_after_analysis` and `route_after_writer`."""
    return "decide_after_critic" if state.get("critic_feedback") is not None else END


def route_after_writer(state: WorkflowState) -> str:
    return "checkpoint_2" if state.get("final_report") is not None else END


def route_after_critic_decision(state: WorkflowState) -> str:
    """Requirement 10: the workflow must terminate even if the Critic keeps
    rejecting the output. The cap itself is enforced by
    `supervisor.decide_after_critic`, which sets `revision_forced_stop`
    explicitly — this function trusts that flag rather than independently
    re-comparing revision_count to max_revisions (comparing the
    ALREADY-incremented revision_count here caused an off-by-one that
    vetoed the last allowed revision cycle before it ever ran).
    """
    feedback = state.get("critic_feedback")
    if feedback is None:
        return "writer"
    decision = feedback.decision if isinstance(feedback.decision, str) else feedback.decision.value
    if decision == "approved":
        return "writer"
    if state.get("revision_forced_stop", False):
        return "writer"  # forced termination — the cap was already reached BEFORE this cycle
    return "analyst"


def route_after_final_checkpoint(state: WorkflowState) -> str:
    if state.get("checkpoint_2_status") == "approved":
        return "finalize"
    # Request Changes -> loop back for one more analyst/critic pass.
    # (Bounded by the same max_revisions cap via revision_count.)
    if state.get("revision_count", 0) >= state.get("max_revisions", 2):
        return "finalize"
    return "analyst"
