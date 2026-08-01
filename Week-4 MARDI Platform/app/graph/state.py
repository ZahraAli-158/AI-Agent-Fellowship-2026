"""
Shared Workflow State — Requirement 8 (Section 16).

This is the single structured object threaded through every node in the
LangGraph graph. Agents read/write specific fields (see docs/workflow_state_spec.md
for the full read/write matrix) instead of passing raw chat history to each
other, per the requirement: "Agents should not rely only on passing long
chat histories to each other."

Fields that can be written by *multiple parallel branches* (evidence, errors,
trace events) use Annotated[..., operator.add] so LangGraph merges them
automatically instead of one branch clobbering another's writes. This is
what makes the parallel research fan-out (Requirement 11) safe.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from app.schemas.evidence import Evidence
from app.schemas.reports import AnalysisOutput, CriticFeedback, FinalReport
from app.schemas.tasks import Task


class CheckpointStatus:
    WAITING = "waiting"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    REQUEST_CHANGES = "request_changes"


class WorkflowStatus:
    PENDING = "pending"
    ANALYZING_REQUEST = "analyzing_request"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    AWAITING_PLAN_APPROVAL = "awaiting_plan_approval"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    REVIEWING = "reviewing"
    REVISING = "revising"
    AWAITING_FINAL_APPROVAL = "awaiting_final_approval"
    WRITING_REPORT = "writing_report"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowState(TypedDict, total=False):
    # --- Request & objective -------------------------------------------------
    run_id: str
    user_request: str
    clarifications: List[str]
    needs_clarification: bool
    clarification_questions: List[str]
    research_objective: Dict[str, Any]  # objective, sub_questions, criteria, constraints, etc.

    # --- Planning -------------------------------------------------------------
    task_plan: List[Task]
    current_tasks: Annotated[List[str], operator.add]
    completed_tasks: Annotated[List[str], operator.add]

    # --- Evidence & analysis (merged across parallel researcher branches) -----
    evidence: Annotated[List[Evidence], operator.add]
    analysis: Optional[AnalysisOutput]
    critic_feedback: Optional[CriticFeedback]
    revision_count: int
    max_revisions: int
    revision_forced_stop: bool  # set by decide_after_critic when the cap was already reached BEFORE this cycle

    # --- Human checkpoints ------------------------------------------------------
    checkpoint_1_status: str
    checkpoint_2_status: str

    # --- Output -----------------------------------------------------------------
    final_report: Optional[FinalReport]

    # --- Observability ------------------------------------------------------------
    errors: Annotated[List[Dict[str, Any]], operator.add]
    trace: Annotated[List[Dict[str, Any]], operator.add]
    workflow_status: str


def new_state(run_id: str, user_request: str, max_revisions: int = 2) -> WorkflowState:
    """Factory for a fresh workflow state."""
    return WorkflowState(
        run_id=run_id,
        user_request=user_request,
        clarifications=[],
        needs_clarification=False,
        clarification_questions=[],
        research_objective={},
        task_plan=[],
        current_tasks=[],
        completed_tasks=[],
        evidence=[],
        analysis=None,
        critic_feedback=None,
        revision_count=0,
        max_revisions=max_revisions,
        checkpoint_1_status=CheckpointStatus.WAITING,
        checkpoint_2_status=CheckpointStatus.WAITING,
        final_report=None,
        errors=[],
        trace=[],
        workflow_status=WorkflowStatus.PENDING,
    )
