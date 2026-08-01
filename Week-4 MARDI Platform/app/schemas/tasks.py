"""
Task Plan schema — Requirement 3 (Section 11).

The Supervisor generates a list of Task objects dynamically, based on
parsing the user's request. Nothing here is hard-coded to a fixed sequence:
the number of research tasks, their descriptions, and their dependencies
are all derived from `research_objective.sub_questions` at runtime.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Priority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AgentRole(str, Enum):
    SUPERVISOR = "Supervisor"
    RESEARCHER = "Researcher"
    ANALYST = "Analyst"
    CRITIC = "Critic"
    WRITER = "Writer"


class Task(BaseModel):
    id: str = Field(..., description="Task ID, e.g. 'R1', 'A1', 'C1', 'W1'")
    description: str
    assigned_agent: AgentRole
    dependencies: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    completed_at: Optional[str] = None
    # Free-form payload so a research task can carry, e.g., which framework
    # or comparison target it is responsible for.
    parameters: dict = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)

    def is_ready(self, completed_task_ids: List[str]) -> bool:
        """A task is ready to run once every dependency has completed."""
        return all(dep in completed_task_ids for dep in self.dependencies)
