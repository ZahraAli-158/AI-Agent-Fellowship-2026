# Week 6 §14/§15 — RAG Evaluation & Failure Classification

Implementation: `evaluation/evaluators/rag_eval.py`. Ground truth for what
SHOULD be retrieved is stored per-case in `expected_source` (a list of
relevant document names, e.g. `["eiffel.txt", "eiffel3.txt"]`, or `[]` when
nothing in the knowledge base is relevant) in `evaluation/dataset.jsonl`'s
10 `E_knowledge_rag` cases — written by the dataset author, not inferred at
evaluation time, so hit-rate/relevance numbers are measured against a real
answer key.

## Metrics measured (retrieval pipeline evaluated separately from generation, per §14)

| Metric | What it measures | agent-system-v3 result |
|---|---|---|
| **Retrieval Hit Rate** | Was the required information present in retrieved chunks? | **100%** (10/10) |
| **Context Relevance** | Were retrieved chunks relevant (precision of retrieval)? | **100%** |
| **Answer Groundedness** | Was the answer supported by retrieved context? (from the LLM judge's `groundedness` score, 1-5, normalized 0-1) | **0.50** — reflects the offline heuristic judge's flat scoring, not the actual answers; see `docs/WEEK6_JUDGE_VS_HUMAN.md` for why this number is a judge-quality artifact, not a real groundedness problem (human review of the same 2 RAG cases in that comparison scored them 4.80/5) |
| **Citation Correctness** | Did citations point to a source that was both retrieved AND actually relevant? | **100%** |
| **Unsupported Claim Rate** | Fraction of answers given (not a "not found" refusal) with no supporting citation/low groundedness | **0%** |

## RAG Failure Classification (§15 — mandatory two-question decision tree)

`evaluation.evaluators.rag_eval.classify_rag_failure(case, actual,
judge_result)` implements the exact decision tree from the spec:

```
Question
   |
   v
Correct Information Retrieved?  (retrieval_hit_rate)
   |
   +---- NO  ----> "retrieval_failure"
   |
   +---- YES
          |
          v
     Correct Answer Generated?  (answer_groundedness >= 0.5)
          |
          +---- NO  ----> "generation_failure"
          +---- YES ----> "success"
```

**agent-system-v3 result: 10/10 classified `success`, 0 retrieval
failures, 0 generation failures.**

## A real retrieval failure was found and fixed during this work

Before a fix, `evaluation/system_under_test.py`'s offline retrieval
stand-in had a bug: its fallback logic treated the mere presence of the
word **"document"** anywhere in a query as license to return the entire
(Eiffel-Tower-only) knowledge base — even for an off-topic question. This
was caught by exactly the mechanism §15 requires: `retrieval_hit_rate`
returned `False` for test case **E02** ("who designed the Statue of
Liberty?"), correctly classifying it as a **retrieval_failure** — and
inspecting the actual response showed why that classification mattered: the
system had genuinely **hallucinated an answer about the Eiffel Tower** in
response to a Statue of Liberty question, with a citation attached, which
the deterministic `eval_citation_presence` check had **missed** (it only
checks "has a citation OR says not-found" — it doesn't check topical
relevance). This is a concrete demonstration of why §15 insists RAG
failures must be diagnosed at the component level rather than reported as
a single "RAG failed" — the citation-presence check alone would have hidden
this bug entirely.

**Fix:** the retrieval fallback was narrowed to only trigger when the query
actually names the subject ("eiffel"/"tower"), not a generic word like
"document(s)". After the fix, E02 correctly returns "I couldn't find
anything about that in your uploaded documents" and is classified
`success` (nothing was expected to be retrieved, and correctly nothing
was).

## Known limitation

This project's knowledge base test fixture (`_KB` in
`system_under_test.py`) intentionally contains only 2 small documents about
one subject (the Eiffel Tower), so retrieval hit-rate/relevance being 100%
reflects a small, well-separated test corpus, not a claim that retrieval is
perfect at production scale with a large, noisy knowledge base. See
`docs/WEEK6_REPORT.md` §7 for other stated limitations.
