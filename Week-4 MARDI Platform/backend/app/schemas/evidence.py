"""
Evidence schema — Requirement 7 (Section 15).

Every research finding produced by a Researcher agent must conform to this
structured format. This is the atomic unit of "truth" that flows through
the rest of the workflow (Analyst, Critic, Writer all consume Evidence
objects, never raw chat text).
"""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class EvidenceType(str, Enum):
    """Research agents must tag each item so downstream agents know how
    much epistemic weight to give it. This is the 'facts vs claims vs
    assumptions vs missing information' distinction required in Section 5.
    """

    FACT = "fact"
    CLAIM = "claim"
    ASSUMPTION = "assumption"
    MISSING_INFORMATION = "missing_information"


class Evidence(BaseModel):
    """A single structured research finding."""

    id: str = Field(..., description="Unique evidence ID, e.g. 'EV-001'")
    claim: str = Field(..., description="The specific claim or finding, in one sentence")
    supporting_text: str = Field(..., description="Summary or excerpt supporting the claim")
    source: str = Field(..., description="URL, document path, or corpus reference")
    source_title: str = Field(..., description="Human-readable title of the source")
    retrieval_date: date
    research_question: str = Field(..., description="Task ID this evidence answers, e.g. 'R2'")
    confidence: ConfidenceLevel
    agent_id: str = Field(..., description="ID of the researcher agent that produced this")
    evidence_type: EvidenceType = EvidenceType.CLAIM

    model_config = ConfigDict(use_enum_values=True)

    def to_summary_line(self) -> str:
        """Compact one-line form used when summarizing evidence for agents
        that should not receive the full evidence store (Context Management,
        Requirement 13)."""
        return f"[{self.id}|{self.confidence}] {self.claim} (source: {self.source_title})"
