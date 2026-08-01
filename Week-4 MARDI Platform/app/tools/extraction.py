"""
Content Extraction Tool — Requirement 6 (Section 14).

Given a corpus document (as returned by the search tool), extracts the
specific sentence(s) most relevant to a research question, rather than
handing the Researcher agent the whole document. This keeps the amount of
raw text that ever reaches an LLM call small and targeted.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


_ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "Mr.", "Dr.")


def _split_sentences(text: str) -> List[str]:
    # Protect known abbreviations from the sentence boundary regex by
    # temporarily swapping their periods for a placeholder.
    protected = text
    for abbr in _ABBREVIATIONS:
        protected = protected.replace(abbr, abbr.replace(".", "\u0000"))

    raw_sentences = re.split(r"(?<=[.!?])\s+", protected)
    return [s.replace("\u0000", ".").strip() for s in raw_sentences if s.strip()]


def extract_relevant_excerpt(doc: Dict[str, Any], research_question: str, max_sentences: int = 2) -> str:
    """Returns the most relevant sentence(s) from a document for a given
    research question, using simple keyword overlap scoring.
    """
    sentences = _split_sentences(doc["content"])
    if not sentences:
        return ""

    q_terms = {t.lower() for t in research_question.split() if len(t) > 2}

    def overlap(sentence: str) -> int:
        s_terms = {t.strip(".,()").lower() for t in sentence.split()}
        return len(q_terms & s_terms)

    ranked = sorted(sentences, key=overlap, reverse=True)
    chosen = ranked[:max_sentences] if any(overlap(s) for s in ranked[:max_sentences]) else sentences[:max_sentences]
    return " ".join(chosen)
