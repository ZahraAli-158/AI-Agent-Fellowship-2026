# Tool Documentation

Covers every tool in `app/tools/` — signature, purpose, inputs/outputs, and
a runnable example for each. (See `docs/tool_permission_boundaries.md` for
*which agent* is allowed to call which tool, and *why*.)

---

## 1. Search Tool — `app/tools/search.py`

```python
def search(query: str, framework_filter: str | None = None, top_k: int = 3) -> Dict[str, Any]
```

Searches the local controlled research corpus (`app/storage/corpus/*.json`)
with naive keyword scoring. Returns `{"query", "hits": [...], "hit_count"}`
— an empty `hits` list is a valid, non-exceptional result (Requirement 14's
"Empty Research Results" handling relies on this).

```python
from app.tools.search import search
result = search("LangGraph state management", framework_filter="LangGraph", top_k=2)
# {"query": "...", "hits": [{...}, {...}], "hit_count": 2}
```

**Used by:** Researcher agent only.

## 2. Content Extraction Tool — `app/tools/extraction.py`

```python
def extract_relevant_excerpt(doc: Dict[str, Any], research_question: str, max_sentences: int = 2) -> str
```

Given one corpus document (as returned by `search`), extracts the most
relevant 1-2 sentences for a specific research question via keyword
overlap scoring — so the Researcher never hands the Analyst an entire raw
document. Protects common abbreviations (`e.g.`, `i.e.`, `etc.`) from being
mis-split as sentence boundaries.

```python
from app.tools.extraction import extract_relevant_excerpt
excerpt = extract_relevant_excerpt(doc, "how is state managed", max_sentences=1)
```

**Used by:** Researcher agent only.

## 3. Evidence Storage Tool — `app/tools/evidence.py`

```python
def store_evidence(evidence_list: List[Evidence], target: List[Evidence]) -> List[Evidence]
```

Deduplicates new evidence by ID against an existing target list, returning
only the genuinely-new items — this is what LangGraph's `operator.add`
reducer merges into `state.evidence` across parallel Researcher branches.

```python
from app.tools.evidence import store_evidence
new_items = store_evidence(incoming_evidence, target=state["evidence"])
```

**Used by:** Researcher agent (writes), indirectly all downstream agents (via retrieval).

## 4. Evidence Retrieval Tool — `app/tools/evidence.py`

```python
def retrieve_evidence(evidence: List[Evidence], research_question: str | None = None, min_confidence: ConfidenceLevel | None = None) -> List[Evidence]
def summarize_evidence_counts(evidence: List[Evidence]) -> Dict[str, Dict[str, int]]
```

Filters the evidence store for exactly what a downstream agent needs
(Requirement 13's context management — agents never receive the full,
unfiltered store), and produces aggregate counts (by research question, by
agent, by confidence) for the dashboard's Evidence panel without needing
every full evidence text.

```python
from app.tools.evidence import retrieve_evidence, summarize_evidence_counts
high_conf = retrieve_evidence(state["evidence"], min_confidence=ConfidenceLevel.HIGH)
summary = summarize_evidence_counts(state["evidence"])
# {"by_research_question": {...}, "by_agent": {...}, "by_confidence": {...}}
```

**Used by:** Analyst (retrieval), Critic (indirectly via Analyst's output), API layer (summary for dashboard).

## 5. Calculator Tool (optional/bonus) — `app/tools/calculator.py`

```python
def weighted_score(criterion_scores: Dict[str, float], weights: Dict[str, float]) -> float
def confidence_distribution(confidences: List[str]) -> Dict[str, float]
```

Whitelisted numeric operations only (never a general-purpose `eval()`,
which would be an arbitrary-code-execution risk — see
`docs/security_review.md` R3). Used to compute weighted comparison scores
and confidence-level percentage breakdowns.

```python
from app.tools.calculator import weighted_score, confidence_distribution
score = weighted_score({"reliability": 8, "cost": 6}, weights={"reliability": 2, "cost": 1})
dist = confidence_distribution(["High", "High", "Low"])  # {"High": 66.7, "Low": 33.3}
```

**Used by:** Analyst agent only.

---

## Adding a new tool

1. Add the function to `app/tools/<name>.py` with type hints and a docstring.
2. Import it only in the agent module(s) that should have access (this is
   what the automated structural test
   `test_tool_permission_boundaries_match_documented_matrix` in
   `tests/test_requirements_coverage.py` checks — a regression here fails CI).
3. Document it here and in `docs/tool_permission_boundaries.md`.
4. Add at least one unit test in `tests/test_schemas_and_tools.py`.
