"""
Analysis, Critic Feedback, and Final Report schemas.

These implement the handoff contracts from Requirement 9 (Section 17):
  Researcher -> Analyst : List[Evidence] (+ gaps, handled in graph/state.py)
  Analyst -> Critic     : AnalysisOutput
  Critic -> Supervisor  : CriticFeedback
  Writer -> User         : FinalReport
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class AnalysisOutput(BaseModel):
    """Handoff contract: Analyst -> Critic."""

    comparison_framework: str = Field(..., description="How the alternatives were compared")
    conclusions: List[str]
    evidence_refs: List[str] = Field(..., description="Evidence IDs cited, e.g. ['EV-001','EV-003']")
    assumptions: List[str] = Field(default_factory=list)
    known_gaps: List[str] = Field(default_factory=list, description="What evidence was missing")


class CriticDecision(str, Enum):
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"


class CriticFeedback(BaseModel):
    """Handoff contract: Critic -> Supervisor."""

    decision: CriticDecision
    problems_found: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    required_revisions: Optional[str] = None
    # Minimum review criteria per Requirement 10
    criteria_scores: dict = Field(
        default_factory=dict,
        description="Score/pass-fail per criterion: evidence_coverage, logical_consistency, "
        "completeness, unsupported_claims, contradictions, relevance",
    )

    model_config = ConfigDict(use_enum_values=True)


class FindingTag(str, Enum):
    EVIDENCE = "evidence"
    ANALYSIS = "analysis"
    RECOMMENDATION = "recommendation"


class Finding(BaseModel):
    tag: FindingTag
    text: str

    model_config = ConfigDict(use_enum_values=True)


class FinalReport(BaseModel):
    title: str
    executive_summary: str
    research_objective: str
    methodology: str
    findings: List[Finding]
    risks_and_limitations: str
    recommendation: str
    evidence_references: List[str] = Field(..., description="Evidence IDs cited in the report")

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", ""]
        lines += ["## Executive Summary", self.executive_summary, ""]
        lines += ["## Research Objective", self.research_objective, ""]
        lines += ["## Methodology", self.methodology, ""]
        lines += ["## Key Findings", ""]
        for f in self.findings:
            lines.append(f"- **[{f.tag.upper() if isinstance(f.tag, str) else f.tag.value.upper()}]** {f.text}")
        lines += ["", "## Risks and Limitations", self.risks_and_limitations, ""]
        lines += ["## Recommendation", self.recommendation, ""]
        lines += ["## Evidence and References"]
        lines += [f"- {eid}" for eid in self.evidence_references]
        return "\n".join(lines)
