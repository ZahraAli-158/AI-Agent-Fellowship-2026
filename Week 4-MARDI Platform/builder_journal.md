# Builder Journal — MARDI Platform (Week 4)

A running account of how this project was actually built, including the
real bugs found and fixed along the way — not a cleaned-up retrospective.

## Phase 1 — Core Multi-Agent Backend

Started with the LangGraph state model (`app/graph/state.py`), since every
other piece depends on its shape. Chose `Annotated[List[X], operator.add]`
reducers specifically for `evidence`, `completed_tasks`, `errors`, and
`trace` — these are the only fields written by parallel branches (the
research fan-out), so they're the only ones that need merge semantics
instead of plain overwrite.

Built the 5 agents in dependency order: Supervisor (request analysis +
dynamic planning) → Researcher (parallel-safe by design, since each
invocation only touches its own `Task`) → Analyst → Critic → Writer. Kept
each agent's mock-mode logic deterministic and topic-aware (a `_detect_topic`
keyword matcher) from the start, specifically so Dynamic Planning
(Requirement 3) would be testable without any API key.

**First real bug:** the sentence extractor in `app/tools/extraction.py`
was splitting sentences at "e.g." and "i.e." mid-abbreviation, corrupting
evidence excerpts. Fixed by protecting known abbreviations before running
the sentence-boundary regex.

## Phase 2 — Human-in-the-Loop, Revision Loop, Parallel Execution

Built the two checkpoints (`app/graph/human.py`) as plain graph nodes
calling an injectable callback, deliberately choosing this over
LangGraph's native `interrupt()` — simpler to test with a canned callback,
and version-stable across LangGraph releases.

**Second bug, more serious:** discovered via Experiment 5
(`docs/experiment_5_revision_limits.md`) that `max_revisions=1` was
silently behaving like `max_revisions=0` — an off-by-one where
`route_after_critic_decision` re-derived the cap check against an
*already-incremented* `revision_count`, vetoing the one revision cycle it
had just allowed. Fixed by having `decide_after_critic` set an explicit
`revision_forced_stop` flag instead of routing re-deriving the same
comparison a second time.

## Phase 3 — Evaluation, Experiments, Adversarial Testing

Built `evaluation/evaluation_dataset.py` to run 25 real scenarios through
the actual workflow rather than hand-writing "expected" results. This
immediately caught two more real defects:

- Missing-evidence runs got stuck showing `workflow_status="researching"`
  forever instead of reaching a terminal `failed` state (the Analyst's
  early-return for zero evidence never set a terminal status).
- An empty-string request wasn't validated and produced a meaningless
  "successful" report.

Both fixed directly in `app/agents/analyst.py` and `app/agents/supervisor.py`.
Also had to correct several of my own scenario *expectations* — a few
requests I'd written as "should complete" were actually requests the
topic-detector correctly has no corpus coverage for, so a clean failure
was the right behavior, not a bug.

Adversarial testing (`tests/test_adversarial.py`) found three more real
gaps (AT-05, AT-07, AT-10) which were initially documented as known
limitations rather than fixed immediately.

## Phase 4 — FastAPI + React Dashboard

Wrapped the existing graph in a REST layer (`app/api.py`) without touching
`app/agents`, `app/graph`, `app/tools`, or `app/schemas` — each run gets a
background thread and a `threading.Event`-based checkpoint blocking
mechanism that reuses the exact same `human_review_callback` contract the
CLI already used.

**Bug found here:** `analyst.py`/`critic.py`/`writer.py` weren't marking
their own task IDs (`A1`/`C1`/`W1`) as completed in `state.completed_tasks`
— only the Researcher tasks were. This made the dashboard's Task Plan tab
show those tasks as stuck "pending" even after a successful run. Fixed by
adding the missing `completed_tasks` entries to each agent's return value.

Built the React dashboard against the real API from the start (no mock
data), verified end-to-end with Playwright screenshots through every tab.

## Phase 5 — Live LLM Integration Bugs (the two most important fixes)

Once real Gemini calls were wired in (`LLM_PROVIDER=gemini`), two
production-only bugs surfaced that mock mode could never have caught:

1. **Indefinite hang, no exception.** A stalled/slow Gemini call could
   block the entire background workflow thread forever with zero
   exceptions raised — the dashboard just sat at `workflow_status="pending"`
   permanently, no error message, nothing in the logs. Root cause: no
   timeout anywhere in `llm_client.py`. Fixed with a hard
   `ThreadPoolExecutor`-based deadline (`LLM_TIMEOUT_S`) that converts a
   hang into a catchable `TimeoutError`.

2. **Schema-mismatched live responses crashing the run.** Gemini
   occasionally returned a nested object (e.g.
   `{"dimensions": [...]}`) where `AnalysisOutput.comparison_framework`
   requires a plain string, raising an uncaught `pydantic.ValidationError`
   that killed the whole run with an unhelpful generic "failed" state.
   Fixed two ways: (a) defensive coercion of common malformed shapes back
   into valid schema fields where recoverable, (b) uniform
   `json.JSONDecodeError` + `ValidationError` catching in
   `analyst.py`/`critic.py`/`writer.py`, matching the handling
   `supervisor.py` already had — this also fully closed the AT-05
   adversarial-test gap that had previously been left as a documented
   limitation rather than fixed.

3. **Test suite silently depending on shell environment.** Running
   `pytest` without explicitly exporting `LLM_MODE=mock` (and with a real
   API key present in `.env`) made the entire test session make real,
   non-deterministic live API calls instead of using the mock — because
   `app/services/llm_client.py`'s singleton resolves its mode once at
   import time. Fixed with `tests/conftest.py`, which forces mock mode
   before any other module import, regardless of `.env` contents.

## Phase 6 — UI/UX Redesign

Rebuilt every dashboard component with a light/dark/system theme, icons,
animated agent pipeline, a 7-stage progress timeline, a collapsible JSON
tree for the State Inspector, recharts-based analytics, and three export
formats (Markdown, PDF via print, Word via an HTML-doc trick) — all
without touching a single backend file, verified by re-running the full
50-test backend suite unchanged afterward. Later, a further dark-theme
visual pass (a pink/purple/indigo gradient palette, ambient glow accents)
was applied the same way — pure CSS/color changes, re-verified against
the unchanged backend suite each time.

## Phase 7 — Manual Testing Hardening Pass (four more production-only bugs)

A further round of manual testing against the deployed-style live-LLM
configuration surfaced four more bugs — none of them reproducible in mock
mode, all of them following the same shape as Phase 5's discoveries:
malformed/edge-case live behavior that the deterministic mock path can
never exercise, plus one pure frontend state bug.

1. **Edit & Continue panel closing itself mid-edit.** Background status
   polling (`usePolling`, ~1s interval) hands `CheckpointModal` a brand-new
   `pending` object on every tick — even when the checkpoint itself hasn't
   changed — because it's freshly parsed JSON each time. A `useEffect`
   keyed on `pending?.payload` (object reference) re-fired on every single
   poll tick and reset `editing` back to `false`, closing the panel a few
   seconds after the user opened it. Fixed by keying the effect on a
   content-based string (`pending.name + JSON.stringify(pending.payload)`)
   instead of the object reference, so it only re-fires when the
   checkpoint's actual content changes.

2. **`analyze_request` failing before task planning on detailed live
   requests.** A live Gemini call for a request needing a long structured
   answer (e.g. a 4-criteria healthcare/cloud comparison) could return
   truncated or prose-wrapped JSON. `analyze_request` only tried once with
   no recovery path, so this failed the whole workflow before
   `create_plan` ever ran — zero tasks, zero evidence, an error counter,
   all within a few seconds. Fixed with a bounded retry loop (reusing
   `TOOL_MAX_RETRIES`), a `_extract_json_object` helper tolerating stray
   prose around the JSON, and a larger token budget for this specific
   call.

3. **Progress bar showing every stage as "completed" on an early
   failure.** The Overview's stage timeline computed `effectiveIndex =
   STAGES.length` whenever `workflowStatus === "failed"`, regardless of
   how far the run actually got — so a run that failed during request
   analysis showed all 7 stages as complete. Fixed by adding a
   `last_active_status` field to `GET /api/runs/{id}/status` (the most
   recent non-terminal status recorded in the trace) and using that to
   find the real failure point instead of assuming "failed" means
   everything finished.

4. **"Request Changes" not incrementing `revision_count`, and Writer
   crashing on a wrong-shaped live report.** Two more gaps in the same
   family as fix #2 above: the human-triggered "Request Changes" decision
   at checkpoint 2 bypassed the node that increments `revision_count`
   (silently never enforcing `max_revisions` on that path either), and
   `generate_report` only caught `(JSONDecodeError, ValidationError)`,
   so a missing `findings` key or a wrong-shaped finding raised an
   uncaught `KeyError`/`TypeError` that crashed the run thread instead of
   failing cleanly. Fixed by incrementing `revision_count` (with the same
   cap check `decide_after_critic` uses) directly inside
   `checkpoint_final_review`, and by giving `generate_report` the same
   broadened exception handling, retry loop, and larger token budget
   already applied to `analyze_request` in fix #2. See
   `docs/known_limitations.md` for the full detail on both.

## What I'd do differently next time

- Add the `conftest.py` mock-mode guard on day one, not after hitting the
  bug it prevents — test isolation from `.env` should be assumed fragile
  by default, not discovered the hard way.
- Write the off-by-one-prone revision-cap logic as a single function from
  the start (one place that both increments *and* decides whether to
  route onward), rather than splitting the increment decision and the
  routing decision into two functions that each re-derive part of the same
  condition.
