"""
Search Tool — Requirement 6 (Section 14).

Searches an approved, controlled local research corpus (per the assignment's
allowance: "If live web access is not available, you may create a controlled
local research corpus"). Only the Researcher agent is permitted to call this
tool (see docs/agent_design_spec.md and the tool permission matrix).

Also implements Search Failure handling (Requirement 14): an empty result
set is returned as a structured "no hits" response rather than raising,
so the calling agent/graph can decide how to proceed (e.g. retry with a
broader query, or log a gap in evidence).
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from app.config import settings


class SearchFailure(Exception):
    pass


def _load_corpus() -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    corpus_dir = settings.research_corpus_path
    if not os.path.isdir(corpus_dir):
        raise SearchFailure(f"Research corpus directory not found: {corpus_dir}")
    for fname in sorted(os.listdir(corpus_dir)):
        if fname.endswith(".json"):
            with open(os.path.join(corpus_dir, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
                docs.extend(data.get("documents", []))
    return docs


_CORPUS_CACHE: List[Dict[str, Any]] | None = None


def search(query: str, framework_filter: str | None = None, top_k: int = 3) -> Dict[str, Any]:
    """Naive keyword search over the local corpus.

    Returns a structured result: {"query", "hits": [...], "hit_count"}.
    An empty `hits` list is a valid, non-exceptional outcome (Search Failure
    handling: empty research results must not crash the workflow).
    """
    global _CORPUS_CACHE
    if _CORPUS_CACHE is None:
        _CORPUS_CACHE = _load_corpus()

    terms = [t.lower() for t in query.split() if len(t) > 2]

    def score(doc: Dict[str, Any]) -> int:
        haystack = f"{doc['title']} {doc['content']} {doc.get('framework', '')}".lower()
        return sum(haystack.count(t) for t in terms)

    candidates = _CORPUS_CACHE
    if framework_filter:
        candidates = [d for d in candidates if framework_filter.lower() in d.get("framework", "").lower()]

    scored = sorted(((score(d), d) for d in candidates), key=lambda x: x[0], reverse=True)
    hits = [d for s, d in scored if s > 0][:top_k]

    return {"query": query, "hits": hits, "hit_count": len(hits)}
