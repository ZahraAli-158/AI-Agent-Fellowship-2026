# Known Limitations

This is the single consolidated reference for everything MARDI does **not**
currently do — pulled together from every place a limitation, constraint,
documented gap, or scope boundary was previously noted individually:
`docs/security_review.md`, `docs/adversarial_testing.md`,
`docs/evaluation_dataset.md`, `docs/deployment.md`,
`docs/context_management.md`, `docs/roadmap.md`, and the root/backend
`README.md` files. Those documents still contain the full narrative and
supporting evidence for each item; this page exists so a reader doesn't
have to hunt across all of them to see the complete picture in one place.

Where a limitation has already been closed by a later fix, it is marked
**(Resolved)** rather than removed, so the history stays intact.

## Table of Contents

- [AI Agents & Planning](#ai-agents--planning)
- [Research, Evidence & Tools](#research-evidence--tools)
- [Workflow Execution](#workflow-execution)
- [LLM Provider Reliability](#llm-provider-reliability)
- [Context Management](#context-management)
- [Security](#security)
- [Deployment & Infrastructure](#deployment--infrastructure)
- [Performance & Scalability](#performance--scalability)
- [Frontend & Testing Coverage](#frontend--testing-coverage)
- [Product Scope Boundaries](#product-scope-boundaries)

---

## AI Agents & Planning

- **Small, keyword-based research corpus.** The local corpus
  (`app/storage/corpus/`) covers three topics (agent frameworks, cloud
  platforms, and RAG/retrieval-augmented enterprise chatbot
  architectures). Any request whose keywords don't match the topic
  detector's keyword list (`framework`, `agent`, `cloud`, `coding
  assistant`, `retrieval-augmented`, `chatbot`, or the standalone word
  "rag") falls back to generic placeholder candidates with zero corpus
  coverage — correctly resulting in a clean `missing_evidence` failure
  rather than a fabricated report (see
  `docs/evaluation_dataset.md` scenarios S05/C01/C04/M04/I03/F04).
- **Keyword matching, not semantic intent.** The topic detector
  (`_detect_topic` in `app/agents/supervisor.py`) matches on literal
  keywords, not meaning — a request naming a specific real tool (e.g.
  "CrewAI") without the word "framework"/"agent" present will not be
  recognized (`docs/adversarial_testing.md` AT-02/AT-10 context,
  `docs/evaluation_dataset.md` I01/I02/I03 notes).
- **Only the first keyword hit is used for multi-topic requests.** A
  request that genuinely spans two topics (e.g. "agent frameworks *and*
  cloud deployment platforms") is researched as if it were a single topic,
  since the detector returns on its first keyword match
  (`docs/evaluation_dataset.md` scenario C05).
- **Fictional/unknown tool names are silently ignored.** A request naming
  fictional or unrecognized products (e.g. "Framework Zeta") still matches
  on a surrounding keyword like "framework" and researches the detector's
  real candidate list instead — evidence is returned, but about different
  products than the ones named, which is a source of potential user
  confusion worth flagging (`docs/evaluation_dataset.md` scenario I02).
- **Planned near-term fix:** replace the keyword-based detector with
  embedding-similarity matching against corpus topics (`docs/roadmap.md`
  item 4), which would close the AT-02/I01/I02/I03 gaps above.

## Research, Evidence & Tools

- **`SearchFailure` is not caught inside `researcher.research_task`.** The
  researcher's retry loop only handles the "zero hits returned" case, not
  an exception raised directly by the `search()` tool (e.g. a missing
  corpus directory). In the full graph this still propagates safely to
  `app/api.py`'s outer try/except (`session.status = "error"`), so the API
  does not crash, but a dedicated try/except around the `search()` call —
  retried once per Requirement 14's stated fallback strategy — would be a
  strictly better fix (`docs/adversarial_testing.md` AT-07).
- **`dispatch_research` does not deduplicate by task ID.** A duplicate
  task in the plan would genuinely be dispatched twice
  (`docs/adversarial_testing.md` AT-10). Low severity in practice since
  the Supervisor's `create_plan` never produces duplicates itself, but not
  defended against if a future change introduced one. (`store_evidence`'s
  dedup-by-ID would still prevent duplicate *evidence* IDs from
  double-counting, provided the researcher assigns IDs deterministically
  per task.)

## Workflow Execution

- **No mid-run objective changes.** There is no API to change
  `user_request` on an already-running workflow
  (`docs/adversarial_testing.md` AT-08). The only way to pursue a
  different objective is to start a new run with a new `run_id`. This is a
  deliberate scope boundary, not an oversight.
- **Off-by-one in the revision cap — (Resolved).** A configured
  `max_revisions=1` was previously silently behaving like
  `max_revisions=0`, vetoing the last allowed revision cycle before the
  Analyst ever got to use it. Found via Experiment 5 and fixed; routing
  now trusts an explicit `revision_forced_stop` flag set by
  `decide_after_critic` instead of re-comparing the already-incremented
  counter (`docs/experiment_5_revision_limits.md`,
  `docs/security_review.md` R9).
- **"Request Changes" at checkpoint 2 didn't increment revision_count —
  (Resolved).** The automatic Critic-rejection loop increments
  `revision_count` via a dedicated `decide_after_critic` node, but the
  human-triggered "Request Changes" decision at checkpoint 2
  (`checkpoint_final_review` in `app/graph/human.py`) routed straight back
  to the Analyst without ever passing through that node, so
  `revision_count` genuinely never changed in state — visible as
  "Revisions: 0 / 2" on the Overview even after a successful revision,
  and consistent everywhere else because there was nothing to be
  inconsistent with. As a side effect, `max_revisions` was silently never
  enforced on this path either. Fixed by incrementing `revision_count`
  (with the same cap check) directly inside `checkpoint_final_review`.

## LLM Provider Reliability

- **Live models don't always follow the requested JSON schema exactly.**
  Gemini in particular has been observed returning a nested object where a
  plain string was required. `analyst.py`/`critic.py`/`writer.py`
  defensively coerce common malformed shapes and cleanly fail (rather than
  crash) on genuinely unrecoverable ones, but a sufficiently different
  malformed response could still produce a clean-but-unhelpful `failed`
  status rather than a fully self-healing one (`docs/security_review.md`
  R9 update, `docs/builder_journal.md` Phase 5).
- **No retry-with-backoff for rate-limited free-tier responses** beyond
  the single configured retry (`TOOL_MAX_RETRIES`).
- **Writer crashed the whole run thread on a wrong-shaped report — (Resolved).**
  `generate_report` (`app/agents/writer.py`) only caught
  `(JSONDecodeError, ValidationError)` around the LLM response, so a
  response missing the `findings` key entirely, or a finding given as a
  plain string instead of a `{tag, text}` object, raised an uncaught
  `KeyError`/`TypeError` that propagated all the way up through
  LangGraph's `stream()` — crashing the run thread (`session.status ==
  "error"`) with no clean `failed` state, no recorded error, and no
  Execution Log entry, instead of failing gracefully. More detailed,
  multi-criteria comparison requests (more findings, more surface area,
  more truncation risk at a tight token budget) made this more likely to
  trigger. Fixed the same way as `analyze_request`: broadened the except
  clause to also catch `(TypeError, KeyError)`, added a bounded retry with
  JSON-extraction, and raised the token budget for this call.
- **Indefinite hang on a stalled live call — (Resolved).** A stalled
  Gemini call could previously block the background workflow thread
  forever with no exception raised. Fixed with a hard
  `ThreadPoolExecutor`-based deadline (`LLM_TIMEOUT_S`) in
  `app/services/llm_client.py` that converts a hang into a catchable
  `TimeoutError` (`docs/builder_journal.md` Phase 5).

## Context Management

- **Token-usage tracking is not wired up.** `LLMResult` in
  `app/services/llm_client.py` is the natural extension point for
  capturing `response.usage.input_tokens` / `output_tokens` from a live
  API response into a structured trace event, but this is not currently
  implemented — intentionally, to avoid making network calls a hard
  requirement for running the test suite (`docs/context_management.md`,
  last section; `docs/roadmap.md` item 6).
- **Context payloads are hand-curated per agent, not algorithmically
  summarized.** This works well at the current evidence-store scale but
  would need a real summarization strategy if evidence volume grew
  substantially larger (`docs/context_management.md`, `docs/roadmap.md`
  item 8).

## Security

Full detail and mitigations for each item live in
`docs/security_review.md` (11 numbered risks, R1–R11). The gaps with no
current mitigation are:

- **No authentication layer.** No login/auth, no per-user rate limiting,
  and no protection against a script bypassing the frontend to resolve
  checkpoints directly (`docs/security_review.md` R7, R10, R11).
- **No cost controls / rate limits.** `LLM_TIMEOUT_S`, `TOOL_MAX_RETRIES`,
  and `max_revisions` bound *per-call* and *per-run* cost, but there is no
  per-user or global rate limit / spend cap — a script hitting `POST
  /api/runs` in a loop could generate unbounded live API cost
  (`docs/security_review.md` R10).
- **Human-approval bypass is possible via the raw API.** `POST
  /api/runs/{id}/checkpoint` accepts and acts on any well-formed decision
  body from any caller — there's no distinction between a human clicking
  "Approve" in the UI and a script sending the same JSON. This is a
  material gap for any deployment where checkpoint integrity matters
  (`docs/security_review.md` R11).
- **No data-retention/expiry policy.** User requests could contain
  sensitive information sent to a third-party LLM provider; `RunSession`
  state is in-memory only (not persisted to disk), which limits but does
  not eliminate exposure (`docs/security_review.md` R5).
- **Residual prompt-injection risk.** A determined injection could still
  influence the *content* of an agent's structured output within its JSON
  schema, even though no tool in the system grants file/env/secret access
  an injected instruction could exploit (`docs/security_review.md` R1).

## Deployment & Infrastructure

Full detail lives in `docs/deployment.md`'s "Documented limitations of the
deployed environment" section. Summary:

- **In-memory run state is lost on redeploy or free-tier sleep.**
  `RunSession` objects live only in the FastAPI process's memory
  (`app/api.py`) — a redeploy or a free-tier cold start wipes run history.
  A production deployment needing persistent history would need to swap
  the in-memory `SESSIONS` dict for a real database (`docs/deployment.md`
  #1; `docs/roadmap.md` item 2).
- **Free-tier cold starts add latency.** The first request after a period
  of inactivity may take 30–60+ seconds while the platform spins the
  container back up — a platform characteristic, not an application bug
  (`docs/deployment.md` #2).
- **No authentication in the deployed environment** (same gap as the
  Security section above; see `docs/deployment.md` #3).
- **Live-mode LLM calls cost real money once deployed publicly**, and
  combined with the lack of rate limiting, an unlisted-but-public URL
  should not be shared widely without first adding cost controls
  (`docs/deployment.md` #4).

## Performance & Scalability

- **Single-process, not horizontally scaled.** The FastAPI backend runs
  workflow executions on Python threads within one process — adequate for
  demo/evaluation traffic, but would need a task queue (e.g. Celery/RQ)
  and a real datastore to scale to many concurrent runs in production
  (`docs/roadmap.md` item 7).

## Frontend & Testing Coverage

- **No automated frontend test suite.** The React dashboard was verified
  end-to-end against the real API via manual Playwright screenshot review
  across every tab, rather than an automated frontend test suite
  (`docs/builder_journal.md`, Phase 4). Backend coverage (`backend/tests/`)
  is automated and run via `pytest`.

## Product Scope Boundaries

These are deliberate design decisions, not oversights:

- No mid-run objective changes (see Workflow Execution above).
- Human-in-the-loop checkpoints use an injectable callback
  (`app/graph/human.py`) rather than LangGraph's native `interrupt()` +
  checkpointer, to keep pause/resume behavior stable across LangGraph
  versions and fully unit-testable without a persistence backend. Native
  `interrupt()` support is tracked as a longer-term roadmap item
  (`docs/roadmap.md` item 9, `backend/README.md`).
- The local research corpus is a deliberate, assignment-permitted
  substitute for live web search, not an oversight (Requirement 6 already
  anticipates this). Swapping in a real web-search/RAG backend is tracked
  as a near-term roadmap item (`docs/roadmap.md` item 3) and would need
  the prompt-injection hardening in `docs/security_review.md` R1/R2
  applied first.

---

For planned work that would close the gaps above, see
[`docs/roadmap.md`](roadmap.md).
