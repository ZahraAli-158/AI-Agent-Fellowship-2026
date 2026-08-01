# Future Roadmap

Prioritized by what would most directly close a gap already identified in
`docs/known_limitations.md` and `docs/security_review.md` — not a generic
wishlist.

## Near-term (would unblock production use)

1. **Authentication + per-user rate limiting** (closes R7/R10/R11 in
   `docs/security_review.md`). Add an auth layer in front of `app/api.py`,
   tie `RunSession` ownership to an authenticated identity, and add a
   spend/rate cap before any public-facing deployment.
2. **Persistent run storage.** Swap the in-memory `SESSIONS` dict in
   `app/api.py` for a real database (Postgres/SQLite), so run history
   survives a redeploy. `app/tools/evidence.py`'s docstring already flags
   this exact trade-off point.
3. **Real web search as an alternative to the local corpus.** Add a
   second `search()` backend behind the same tool interface (Requirement 6
   already anticipates this: "if live web access is not available, you
   may create a controlled local research corpus"). Would need the
   prompt-injection hardening flagged in `docs/security_review.md` R1/R2
   applied first, since untrusted web content is a materially different
   risk profile than the reviewed local corpus.

## Medium-term (quality and coverage improvements)

4. **Semantic topic detection.** Replace the keyword-based `_detect_topic`
   in `app/agents/supervisor.py` with an embedding-similarity match against
   corpus topics, closing the AT-02/I01/I02/I03 gaps where a real tool name
   without an exact keyword match falls back to generic (uncovered)
   candidates.
5. **Bonus specialist agents** (Section 6 of the assignment — optional).
   A Fact-Checking Agent or Citation Agent would slot cleanly into the
   existing Critic → Writer handoff without changing the graph shape.
6. **Token-usage tracking per agent**, wiring up the `usage` field already
   available on live Anthropic/Gemini responses into the existing trace
   event system (`docs/context_management.md` flags exactly this as the
   natural extension point).

## Longer-term (scale)

7. **Task-queue-backed execution** (Celery/RQ + Redis) instead of one
   background thread per run, to support many concurrent runs without one
   Python process's GIL becoming the bottleneck.
8. **Evidence summarization strategy** for corpora much larger than the
   current two-topic demo set, replacing the hand-curated per-agent
   context payloads described in `docs/context_management.md` with an
   algorithmic compression step once evidence volume outgrows what fits
   comfortably in a single prompt.
9. **Native LangGraph `interrupt()` + checkpointer** for human checkpoints,
   replacing the current callback-based blocking (`app/graph/human.py`) —
   deliberately deferred in this build for test-simplicity and
   version-stability (see `backend/README.md`'s note on this), but would
   enable true pause/resume across backend restarts.
