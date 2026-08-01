"""
Calculator Tool — optional tool per Requirement 6, granted to the Analyst
agent for simple scoring/aggregation (e.g. weighting comparison criteria).
Deliberately not a general-purpose eval() — only whitelisted operations,
so this cannot be abused as an arbitrary-code-execution vector.
"""
from __future__ import annotations

from typing import Dict, List


def weighted_score(criterion_scores: Dict[str, float], weights: Dict[str, float]) -> float:
    """Computes a weighted average, e.g. for scoring frameworks across
    multiple comparison criteria. Missing weights default to equal weight."""
    if not criterion_scores:
        return 0.0
    total_weight = sum(weights.get(k, 1.0) for k in criterion_scores)
    if total_weight == 0:
        return 0.0
    return sum(criterion_scores[k] * weights.get(k, 1.0) for k in criterion_scores) / total_weight


def confidence_distribution(confidences: List[str]) -> Dict[str, float]:
    """Returns the percentage share of each confidence level."""
    if not confidences:
        return {}
    total = len(confidences)
    counts: Dict[str, int] = {}
    for c in confidences:
        counts[c] = counts.get(c, 0) + 1
    return {k: round(100 * v / total, 1) for k, v in counts.items()}
