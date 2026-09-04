"""
Week 6 — Requirement 5 (RAG Evaluation) + §15 (RAG Failure Classification).

Evaluates the retrieval pipeline SEPARATELY from answer generation, per
§14: "If your system uses RAG, evaluate the retrieval pipeline separately
from answer generation." Ground truth for what SHOULD be retrieved comes
from each Category E case's `expected_source` field (a list of relevant
document names — see evaluation/generate_dataset.py), populated by the
person who wrote the dataset, not inferred at evaluation time.

Only applies to `category == "E_knowledge_rag"` cases; other categories
return None for these metrics (they're not RAG questions).
"""
import re


def is_rag_case(case):
    return case.get("category") == "E_knowledge_rag"


def retrieval_hit_rate(case, actual):
    """Was the required information present in retrieved chunks?
    True if every expected-relevant doc (if any exist) was retrieved, and
    also True for cases with an empty expected_source (nothing SHOULD be
    retrieved) as long as nothing incorrect was retrieved."""
    if not is_rag_case(case):
        return None
    expected = set(case.get("expected_source") or [])
    retrieved = set(actual.get("retrieved_doc_ids") or [])
    if not expected:
        return len(retrieved) == 0  # correctly retrieved nothing
    return expected.issubset(retrieved)


def context_relevance(case, actual):
    """Were retrieved chunks relevant? Precision of retrieval: fraction of
    retrieved docs that were actually in the expected-relevant set."""
    if not is_rag_case(case):
        return None
    expected = set(case.get("expected_source") or [])
    retrieved = set(actual.get("retrieved_doc_ids") or [])
    if not retrieved:
        return 1.0 if not expected else 0.0  # nothing retrieved: relevant iff nothing was expected either
    relevant_retrieved = retrieved & expected
    return round(len(relevant_retrieved) / len(retrieved), 4)


def answer_groundedness(case, actual, judge_result=None):
    """Was the answer supported by retrieved context? Uses the LLM judge's
    `groundedness` score (1-5) when available, normalized to 0-1; falls
    back to a keyword-overlap heuristic against retrieved doc content when
    no judge score was computed (run_judge=False)."""
    if not is_rag_case(case):
        return None
    if judge_result and "groundedness" in judge_result:
        return round((judge_result["groundedness"] - 1) / 4, 4)  # 1-5 -> 0-1
    # Heuristic fallback: an explicit "not found" answer on an empty-expected
    # case is fully grounded; otherwise assume ungrounded without a judge.
    expected = case.get("expected_source") or []
    text = (actual.get("response_text") or "").lower()
    not_found = bool(re.search(r"couldn't find|not in your (uploaded )?documents|no (matching )?information",
                                 text))
    if not expected:
        return 1.0 if not_found else 0.0
    return None  # unknown without a judge score


def citation_correctness(case, actual):
    """Did citations point to supporting evidence? Fraction of cited
    sources that are both (a) actually retrieved AND (b) in the
    expected-relevant set."""
    if not is_rag_case(case):
        return None
    citations = set(actual.get("citations") or [])
    if not citations:
        return None  # nothing to score
    retrieved = set(actual.get("retrieved_doc_ids") or [])
    expected = set(case.get("expected_source") or [])
    correct = citations & retrieved & expected
    return round(len(correct) / len(citations), 4)


def unsupported_claim_rate(rag_results):
    """How frequently did answers contain claims unsupported by retrieved
    context? Computed at the SUITE level (not per-case): fraction of RAG
    cases where an answer was given (not a "not found" refusal) but no
    citation/retrieved doc backed it, or groundedness scored poorly."""
    scoreable = [r for r in rag_results if r.get("answer_groundedness") is not None]
    if not scoreable:
        return None
    unsupported = sum(1 for r in scoreable if r["answer_groundedness"] < 0.5)
    return round(unsupported / len(scoreable), 4)


def classify_rag_failure(case, actual, judge_result=None):
    """Week 6 §15 — the mandatory two-question decision tree. Returns one
    of: 'not_applicable', 'retrieval_failure', 'generation_failure', 'success'."""
    if not is_rag_case(case):
        return "not_applicable"

    hit = retrieval_hit_rate(case, actual)
    if not hit:
        return "retrieval_failure"  # Q1: correct information retrieved? -> NO

    # Q1 = YES. Q2: correct answer generated from what was retrieved?
    grounded = answer_groundedness(case, actual, judge_result)
    if grounded is not None and grounded < 0.5:
        return "generation_failure"
    return "success"


def evaluate_rag_case(case, actual, judge_result=None):
    """Bundles all five RAG metrics + the failure classification for one case."""
    return {
        "retrieval_hit_rate": retrieval_hit_rate(case, actual),
        "context_relevance": context_relevance(case, actual),
        "answer_groundedness": answer_groundedness(case, actual, judge_result),
        "citation_correctness": citation_correctness(case, actual),
        "rag_failure_class": classify_rag_failure(case, actual, judge_result),
    }


def aggregate_rag_metrics(rag_results):
    """Suite-level RAG report: overall Retrieval Hit Rate, Context
    Relevance, Answer Groundedness, Citation Correctness, and Unsupported
    Claim Rate, plus a breakdown of failure classes."""
    def _avg(key):
        vals = [r[key] for r in rag_results if r.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    failure_counts = {}
    for r in rag_results:
        cls = r.get("rag_failure_class", "not_applicable")
        failure_counts[cls] = failure_counts.get(cls, 0) + 1

    return {
        "n_rag_cases": len(rag_results),
        "retrieval_hit_rate": _avg("retrieval_hit_rate"),
        "context_relevance": _avg("context_relevance"),
        "answer_groundedness": _avg("answer_groundedness"),
        "citation_correctness": _avg("citation_correctness"),
        "unsupported_claim_rate": unsupported_claim_rate(rag_results),
        "failure_breakdown": failure_counts,
    }
