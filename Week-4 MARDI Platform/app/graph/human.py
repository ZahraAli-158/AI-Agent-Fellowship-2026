"""
Human-in-the-Loop Checkpoints — Requirement 12 (Section 20).

Implemented as ordinary graph nodes that call an injectable
`human_review_callback(checkpoint_name, payload) -> dict`, rather than
LangGraph's native interrupt()/checkpointer mechanism. This is a deliberate
simplification: it keeps the exact pause/resume behavior stable across
LangGraph versions and fully unit-testable (a test can inject a canned
callback), while still guaranteeing a human decision is required at both
checkpoints before the workflow proceeds.

Three checkpoints are implemented:
  - Clarification  (Requirement 2 — not one of the two "recommended"
    checkpoints, but explicitly required by Requirement 2)
  - Checkpoint 1: Research Plan Approval
  - Checkpoint 2: Final Recommendation Review

Documented human-controlled decisions (see docs for the full write-up):
  - Whether an ambiguous request may proceed without clarification: HUMAN.
  - Whether the research plan may be executed (and at what cost/scope): HUMAN.
  - Whether the final recommendation is accepted: HUMAN.
  - Which sources to search, how to weigh evidence, and revision-loop
    mechanics: AGENT (not surfaced as a per-step human decision).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from app.graph.state import CheckpointStatus, WorkflowState, WorkflowStatus
from app.observability import tracer

HumanCallback = Callable[[str, Dict[str, Any]], Dict[str, Any]]


def auto_approve_callback(checkpoint_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Default non-interactive callback: approves everything and answers
    clarification questions with a reasonable generic default. Used in
    tests, CI, and grading runs where no human is available to type input.
    """
    if checkpoint_name == "clarification":
        return {"answers": ["General engineering use case", "Prototype stage", "No strict language constraint"]}
    return {"decision": "approved"}


def cli_callback(checkpoint_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Interactive callback used by app/main.py's CLI demo."""
    print(f"\n--- HUMAN CHECKPOINT: {checkpoint_name} ---")
    for k, v in payload.items():
        print(f"{k}: {v}")
    if checkpoint_name == "clarification":
        answers = []
        for q in payload.get("questions", []):
            answers.append(input(f"  > {q}\n  answer: "))
        return {"answers": answers}
    decision = input("Decision [approve/edit/reject] (default approve): ").strip().lower() or "approve"
    mapping = {"approve": "approved", "edit": "edited", "reject": "rejected"}
    return {"decision": mapping.get(decision, "approved")}


def request_clarification(state: WorkflowState, callback: HumanCallback) -> Dict[str, Any]:
    trace: List[Dict[str, Any]] = []
    payload = {"questions": state.get("clarification_questions", [])}
    response = callback("clarification", payload)
    trace.append(tracer.human_approval("clarification", "answered"))
    trace.append(tracer.status_change(WorkflowStatus.ANALYZING_REQUEST))
    return {
        "clarifications": response.get("answers", []),
        "needs_clarification": False,
        "workflow_status": WorkflowStatus.ANALYZING_REQUEST,
        "trace": trace,
    }


def checkpoint_plan_approval(state: WorkflowState, callback: HumanCallback) -> Dict[str, Any]:
    trace: List[Dict[str, Any]] = []
    payload = {
        "objective": state["research_objective"].get("objective"),
        "planned_tasks": [t.id + ": " + t.description for t in state["task_plan"]],
        "expected_output": "Comparison report and recommendation",
    }
    response = callback("checkpoint_1_plan_approval", payload)
    decision = response.get("decision", "approved")
    status_map = {
        "approved": CheckpointStatus.APPROVED,
        "edited": CheckpointStatus.EDITED,
        "rejected": CheckpointStatus.REJECTED,
    }
    trace.append(tracer.human_approval("checkpoint_1_plan_approval", decision))
    new_status = WorkflowStatus.RESEARCHING if decision in ("approved", "edited") else WorkflowStatus.FAILED
    trace.append(tracer.status_change(new_status))

    updates: Dict[str, Any] = {
        "checkpoint_1_status": status_map.get(decision, CheckpointStatus.APPROVED),
        "workflow_status": new_status,
    }

    if decision == "edited":
        fields_changed: List[str] = []

        edited_objective = response.get("research_objective")
        additional_instructions = response.get("additional_instructions")
        if edited_objective or additional_instructions:
            new_objective = dict(state["research_objective"])
            if edited_objective:
                new_objective["objective"] = edited_objective
                fields_changed.append("research_objective")
            if additional_instructions:
                new_objective["additional_instructions"] = additional_instructions
                fields_changed.append("additional_instructions")
            updates["research_objective"] = new_objective

        edited_tasks = response.get("task_edits")
        if edited_tasks:
            desc_by_id = {
                t.get("id"): t.get("description", "").strip()
                for t in edited_tasks
                if t.get("id") and t.get("description", "").strip()
            }
            if desc_by_id:
                new_plan = [
                    t.model_copy(update={"description": desc_by_id[t.id]}) if t.id in desc_by_id else t
                    for t in state["task_plan"]
                ]
                updates["task_plan"] = new_plan
                fields_changed.append("task_plan")

        if fields_changed:
            trace.append(tracer.edited("checkpoint_1_plan_approval", fields_changed))

    updates["trace"] = trace
    return updates


def checkpoint_final_review(state: WorkflowState, callback: HumanCallback) -> Dict[str, Any]:
    trace: List[Dict[str, Any]] = []
    payload = {
        "title": state["final_report"].title,
        "recommendation": state["final_report"].recommendation,
    }
    response = callback("checkpoint_2_final_review", payload)
    decision = response.get("decision", "approved")
    status_map = {"approved": CheckpointStatus.APPROVED, "request_changes": CheckpointStatus.REQUEST_CHANGES}
    trace.append(tracer.human_approval("checkpoint_2_final_review", decision))

    if decision != "request_changes":
        new_status = WorkflowStatus.COMPLETED
        trace.append(tracer.status_change(new_status))
        return {
            "checkpoint_2_status": status_map.get(decision, CheckpointStatus.APPROVED),
            "workflow_status": new_status,
            "trace": trace,
        }

    # "Request Changes" is a second, human-triggered entry point into the
    # same bounded revision loop the Critic's automatic rejection uses —
    # so it must increment revision_count exactly the same way
    # decide_after_critic does. Previously this branch only set
    # workflow_status to REVISING and returned to the Analyst, without
    # ever touching revision_count: the Overview/State Inspector/Execution
    # Log correctly showed 0 because the backend state genuinely never
    # changed it, and route_after_final_checkpoint's `revision_count >=
    # max_revisions` cap check was silently never true on this path either
    # (unbounded "Request Changes" clicks).
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 2)
    new_status = WorkflowStatus.REVISING

    if revision_count >= max_revisions:
        # Cap already reached — record the decision but don't increment
        # again. route_after_final_checkpoint will send this to "finalize"
        # rather than back to the Analyst.
        trace.append(tracer.status_change(new_status))
        return {
            "checkpoint_2_status": CheckpointStatus.REQUEST_CHANGES,
            "workflow_status": new_status,
            "trace": trace,
        }

    new_count = revision_count + 1
    trace.append(tracer.revision(new_count, max_revisions, "human requested changes at checkpoint_2_final_review"))
    trace.append(tracer.status_change(new_status))
    return {
        "checkpoint_2_status": CheckpointStatus.REQUEST_CHANGES,
        "workflow_status": new_status,
        "revision_count": new_count,
        "trace": trace,
    }
