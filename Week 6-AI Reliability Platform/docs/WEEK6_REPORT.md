# Week 6 Report — Reliable and Observable Production AI System

**Foundation project:** Week 5 — AI Workspace Platform (Flask + Gemini API,
multi-workspace chat, RAG knowledge base, Meeting Agent with tools, prompt
library, usage dashboard).
**Engineering principle followed:** Measure → Test → Observe → Diagnose →
Improve → Re-evaluate (§5).

This report is the entry point; detailed evidence lives in the companion
docs listed at the bottom.

## Headline results

| Metric | Baseline (`baseline_v1`, prompt v1) | Final (`agent-system-v3`, prompt v3) |
|---|---|---|
| Task success rate | 91.94% (57/62) | **100% (62/62)** |
| RAG retrieval hit rate / context relevance / citation correctness | not measured | **100% / 100% / 100%** |
| Agent evaluation (intent, planning, state, recovery) | not measured | **100%** across all four |
| Tool selection accuracy | 100% | 100% |
| Production readiness score | 25/100 | **90/100** |
| Automated tests | 62 (Week 1–5 only) | **241** (179 new Week 6 tests) |

Five real bugs were found and fixed during this work (three routing/
extraction bugs, one RAG hallucination bug, and one **live security gap**
where the permission/approval system existed but was never actually wired
into the agent's tool-execution path) — see
`docs/WEEK6_ROOT_CAUSE_ANALYSIS.md` for the full account of each.

## 1. Architecture

Implemented largely per the suggested §6 diagram, adapted to the existing
Flask app rather than a fresh scaffold:

```
User -> app.guardrails.input (validation + injection defense)
     -> AI Application (app.routes.chat_routes / app.services.agent_service)
         |- RAG (app.services.embedding_service, scanned per-chunk before use)
         |- Agents (Meeting Agent tools, LangGraph agents from Week 4/5)
         `- Tools (app.guardrails.permissions L0-L4 risk gate, ENFORCED live
                    in delete_task/send_email_summary, not just documented)
     -> app.guardrails.output (schema/citation/URL/tool-action validation)
     -> Response
         |
     app.observability
         |- tracing.py   -> Trace / TraceStep (DB), one step per pipeline
         |                 stage: model_call, retrieval, agent_decision,
         |                 tool_call (one per tool actually invoked)
         |- logging.py   -> structured JSON events
         |- metrics.py   -> latency/reliability/usage aggregation
         `- cost.py      -> per-request & aggregate cost
     -> evaluation/
         |- dataset.jsonl (62 cases) + generate_dataset.py
         |- evaluators/deterministic.py, rag_eval.py, agent_eval.py
         |- judge.py (LLM-as-judge + documented limitations)
         |- human_eval.py (Sec12 judge-vs-human comparison)
         |- runner.py (full pipeline, writes filled dataset back out)
         `- regression.py (baseline comparison)
     -> app/templates/observability_dashboard.html + trace_viewer.html
       (trace viewer groups steps into the required pipeline stages)
```

Justification for deviating from the spec's diagram: rather than a
standalone `production-ai-system/` scaffold, this was built **inside** the
existing Week 5 Flask app (`app/observability/`, `app/guardrails/`,
`app/reliability/`, plus a top-level `evaluation/`, `prompts/`, `docs/`)
so the reliability layer is actually wired into real, running routes
(`chat_routes.send_message`, `agent_routes.send_message`,
`agent_service.run_agent_turn`) rather than existing only as a parallel
demo.

## 2. What was built, mapped to spec requirements

| Requirement | Where |
|---|---|
| R1 Evaluation Dataset (60+ cases, 6 categories) | `evaluation/dataset.jsonl` (62 cases), `evaluation/generate_dataset.py` |
| R2 Deterministic Evaluators | `evaluation/evaluators/deterministic.py` |
| R3 LLM-as-a-Judge | `evaluation/judge.py` (documented prompt + 1-5 structured scoring) |
| R4 Task Success Evaluation | `docs/WEEK6_TASK_SUCCESS_DEFINITION.md` — exact pass/fail definition, overall/by-category/failure-by-category all reported in every `reports/<label>.json` |
| R5 RAG Evaluation | `evaluation/evaluators/rag_eval.py` — all 5 metrics, `docs/WEEK6_RAG_EVALUATION.md` |
| R6 RAG Failure Classification | `rag_eval.classify_rag_failure` — the exact two-question decision tree, code + doc |
| R7 Agent Evaluation | `evaluation/evaluators/agent_eval.py`, `docs/WEEK6_AGENT_EVALUATION.md` |
| R8 Execution Tracing | `app/observability/tracing.py`, `Trace`/`TraceStep` models, wired into both `chat_routes.py` and `agent_service.run_agent_turn` (including one `tool_call` step per tool actually invoked) |
| R9 Trace Viewer | `app/templates/trace_viewer.html`, `/observability/trace/<id>` — groups steps into Model Call / Retrieval / Agent Decision / Tool Call-Result |
| R10 Structured Logging | `app/observability/logging.py` — all 11 required event types actually logged (not just defined): `request_received`/`retrieval_started`/`retrieval_completed`/`model_called` in `chat_routes.py`; `tool_selected`/`tool_succeeded`/`tool_failed` in `agent_service.py`'s tool wrapper; `retry_attempted`/`guardrail_triggered`/`request_completed` across both; `evaluation_completed` in `evaluation/runner.py` |
| R11 Quality Dashboard | `app/templates/observability_dashboard.html`, `/observability/` — Quality (task success/judge score/RAG groundedness/tool accuracy/failure rate), Reliability (successful/failed requests, retry rate, **timeout rate**, guardrail triggers), Performance (avg/**P50**/P95 latency), Usage (**input/output/total tokens**, requests), Cost (total + **avg cost per request**), and **by-model / by-date / by-test-category breakdown tables** |
| R12 Prompt Versioning | `prompts/v1.txt` - `v3.txt`, `prompts/registry.py`, `prompts/metadata.json` — `evaluation_score` is now written back automatically by `evaluation/runner.py` after each run (was previously always `null`); confirmed v1=0.9194, v2=0.9355, v3=1.0 |
| R13 Prompt Regression Testing | `evaluation/regression.py` — see `docs/WEEK6_EXPERIMENTS.md` Exp. 1 |
| R14 Model Comparison | `evaluation/system_under_test.run_live` supports `--model`; see Exp. 2 (honest limitation noted) |
| R15 Input Guardrails | `app/guardrails/input.py` — empty/long/malformed/injection/**unsupported-operation** checks all implemented |
| R16 Prompt Injection Testing (15+) | 8 in `evaluation/dataset.jsonl` (Category F) + 10 direct unit tests in `tests/test_week6_guardrails.py` = **18 total** |
| R17 Indirect Prompt Injection | `scan_retrieved_document`, wired into `chat_routes.send_message` |
| R18 Output Guardrails | `app/guardrails/output.py` — schema, missing fields, **tool-argument validation**, citations, unauthorized actions, URLs, and **output-type validation** all implemented |
| R19 Tool Security (risk levels) | `app/guardrails/permissions.py` (L0-L4), **enforced live** in `agent_service.py`'s `delete_task`/`send_email_summary` |
| R20 Failure Injection | `tests/test_week6_failure_injection.py` |
| R21 Retry Strategy | `app/reliability/retries.py`, wired live into `chat_routes.py`'s model call — see `docs/WEEK6_RELIABILITY.md` for the full retryable/non-retryable classification and configured max-retries/delay/backoff |
| R22 Timeout Handling | `app/reliability/timeouts.py`, wired live into model calls, retrieval, and agent workflow steps (`chat_routes.py`, `agent_service.py`) — not just available as a library |
| R23 Agent Loop Prevention | `app/reliability/loop_prevention.py`, wired into `agent_service.run_agent_turn`'s live tool-call loop, incl. duplicate-action detection and an execution timeout |
| R24 Graceful Degradation | `app/reliability/fallback.py` — 3 scenarios documented in §4 below |
| R25 Cost Tracking | `app/observability/cost.py` — per-request input/output/total cost, plus aggregation by model, by agent, and by feature (`cost_by_model`/`cost_by_agent`/`cost_by_feature`), all surfaced on the dashboard |
| R26 Latency Analysis | `app/observability/latency_analysis.py` — LLM/retrieval/tool/end-to-end latency broken out from real Trace/TraceStep data with mean/median/P50/P95 and automatic bottleneck identification; database latency honestly reported as not separately measured (local SQLite, no per-statement instrumentation) rather than fabricated |
| R27 Optimization (3+) | `docs/WEEK6_EXPERIMENTS.md` Experiment 7 (5 optimizations) |
| R28 Required Experiments (7) | `docs/WEEK6_EXPERIMENTS.md` — all 7 actually run, not narrated; Experiments 3 and 5 use dedicated runnable scripts (`evaluation/experiment_retrieval_topk.py`, `evaluation/experiment_guardrails.py`) that produce real measured JSON output |
| R29 Human Evaluation | `docs/WEEK6_JUDGE_VS_HUMAN.md` (11 cases, real comparison) + §5 below |
| R30 Failure Taxonomy | `docs/WEEK6_FAILURE_TAXONOMY.md` + `evaluation/evaluators/failure_taxonomy.py` — every FAIL result is auto-assigned an F01-F14 code in code, not just documented as a category system |
| R31 Root Cause Analysis (10) | `docs/WEEK6_ROOT_CAUSE_ANALYSIS.md` — 6 real findings + 4 anticipated; codes reconciled against the automated classifier (see §10 below) |
| R32 Evaluation Pipeline | `evaluation/runner.py` (single command, no manual copy/paste, writes filled dataset back out per §9) |
| R33 Regression Testing | `evaluation/regression.py` |
| R34 Release Gate | `docs/WEEK6_RELEASE_GATE.md` |
| R35 Production Readiness Score | `docs/WEEK6_PRODUCTION_READINESS.md` (25→91/100), recomputable via `evaluation/release_gate.py` for the score's threshold-based criteria |
| R36 Security Review (10+ risks) | `docs/WEEK6_SECURITY_REVIEW.md` — 15 risks, explicit coverage checklist against all 14 required categories, 2 fixed live during this work |
| R37 Observability Dashboard | `/observability/` route — every §47 category covered: System Health (incl. Active Errors), AI Quality, Performance (P50/P95), Usage (incl. separate Model Calls/Tool Calls), Cost (incl. per-request/per-successful-task), Security |
| R38 Automated Testing (25+) | 179 new tests across `tests/test_week6_*.py` |
| R39 Code Quality | modular packages, type-hinted where practical, structured logging, prompt/eval config, reusable evaluators, error handling, retries, timeouts, tests, docs (this report) |

## 3. RAG Failure Classification (§15, §6 core project) — see `docs/WEEK6_RAG_EVALUATION.md` for full detail

Implemented as a two-question decision, not a single "RAG failed" verdict,
in `evaluation.evaluators.rag_eval.classify_rag_failure`. Building this
evaluator caught a real bug: the offline retrieval stand-in was returning
the entire (Eiffel-Tower-only) knowledge base for an unrelated Statue of
Liberty question (E02), and the system had **hallucinated an Eiffel Tower
answer, with a citation attached** — something the original deterministic
citation-presence check had completely missed, because it only checks
"has a citation OR says not-found," not topical relevance. This is exactly
why §15 insists on component-level diagnosis. Fixed; final result on the
10 `E_knowledge_rag` cases: **10/10 classified `success`, 0 retrieval
failures, 0 generation failures.**

## 4. Graceful Degradation — 3 documented scenarios (§20, §33)

Implemented in `app/reliability/fallback.py`, each with a dedicated test:

1. **Vector DB / retrieval failure** → `safe_retrieval()` returns an empty
   result set plus the message *"Knowledge search is temporarily
   unavailable..."* instead of crashing the request. Verified by
   `test_vector_db_unavailable_degrades_instead_of_crashing`.
2. **Primary model failure** → `safe_model_call()` falls back to a second
   callable instead of surfacing a 500. Verified by
   `test_llm_api_unavailable_falls_back_gracefully`. In `chat_routes.py`,
   the primary Gemini call is additionally wrapped in `call_with_retry`
   before this fallback would even be needed.
3. **Tool failure** → `safe_tool_call()` returns a partial result with an
   explanatory message instead of aborting the whole agent turn. Verified
   by `test_tool_throws_exception_returns_partial_result`.

## 5. Human Evaluation & LLM Judge vs Human Score (§12, §39)

**§12 requirement (LLM Judge Score vs Human Score for ≥10 cases,
discussing disagreements) — done:** see **`docs/WEEK6_JUDGE_VS_HUMAN.md`**.
11 baseline_v1 cases were scored by hand against the same 5-criterion
rubric the judge uses. Mean absolute disagreement was **1.35/5** — the
offline heuristic judge (used because no live API key is configured for
this submission) returns a near-flat score regardless of actual response
quality, both under-rating genuinely good answers and over-rating
genuinely broken ones. This is real, measured evidence for the judge-bias
concerns §12 asks the report to discuss.

**§39 requirement (two independent human evaluators score 10 outputs) —
honestly scoped, not done:** this submission was completed by a single
developer without access to two independent third-party evaluators in the
time available. `evaluation/human_eval.py`'s `HUMAN_SCORES` dict is the
exact place a second/third evaluator's independent scores would be added
to turn this into a genuine multi-rater comparison.

## 6. Automated Testing Summary (§48)

| File | Tests |
|---|---|
| `tests/test_week6_guardrails.py` | 28 |
| `tests/test_week6_guardrails_extra.py` | 11 |
| `tests/test_week6_reliability.py` | 15 |
| `tests/test_week6_evaluation.py` | 23 |
| `tests/test_week6_tracing.py` | 6 |
| `tests/test_week6_failure_injection.py` | 10 |
| `tests/test_week6_agent_permissions.py` | 4 |
| `tests/test_week6_rag_agent_eval.py` | 20 |
| `tests/test_week6_logging_dashboard.py` | 12 |
| `tests/test_week6_cost_latency.py` | 11 |
| `tests/test_week6_experiments.py` | 7 |
| `tests/test_week6_failure_taxonomy.py` | 12 |
| `tests/test_week6_pydantic_schemas.py` | 12 |
| `tests/test_week6_release_gate.py` | 8 |
| **Week 6 total** | **179** (spec minimum: 25) |
| Full project total (Week 1-6 combined) | **241**, all passing |

Run with: `python -m pytest tests/ -q`

## 7. Known limitations (stated plainly, not hidden)

- The offline evaluation harness (`system_under_test.run_offline_baseline`)
  is a **rule-based stand-in** for a live LLM, used so the full 62-case
  suite, regression testing, and CI-style pytest run work with zero API
  key setup. It is not a substitute for a live-mode run before real
  production release — see `docs/WEEK6_RELEASE_GATE.md`.
- Model comparison (Experiment 2) and P95 latency against the release gate
  both require `--mode live` with a funded `GEMINI_API_KEY` to produce real
  numbers; the harness supports this today but wasn't run against a paid
  key for this submission.
- Human evaluation (§39) is scaffolded and partially executed (§12's
  judge-vs-human comparison is real) but not yet done by two independent
  reviewers.
- The live tool-permission approval gate (fixed this week — see
  `docs/WEEK6_SECURITY_REVIEW.md` risk #4) has no UI control yet for a user
  to actually grant approval; today every agent-initiated `delete_task`/
  `send_email_summary` call will be refused rather than genuinely approved
  end-to-end, until a "confirm" checkbox is added to the chat UI.
- Multi-agent metrics (§16) are explicitly marked `not applicable` since
  the Meeting Agent is a single agent with multiple tools, not a
  multi-agent handoff system — see `docs/WEEK6_AGENT_EVALUATION.md`.
- One open security gap remains genuinely unmitigated: no account/IP-level
  rate limiting (`docs/WEEK6_SECURITY_REVIEW.md` risk #6).

## 8. Structured logging, dashboard, and guardrail completeness audit (§19-28)

A follow-up audit against the spec's exact checklists for these sections
found several gaps between what was *documented* and what was actually
*implemented and running*:

- **§19**: 5 of the 11 required structured-log event types
  (`retrieval_started`, `tool_selected`, `tool_succeeded`, `tool_failed`,
  `evaluation_completed`) were defined in `EVENT_TYPES` but never actually
  emitted anywhere in the code. Now wired in.
- **§20**: the live `/observability/` dashboard was missing P50 latency,
  separate input/output token counts, avg cost per request, timeout rate,
  RAG groundedness, and agent-evaluation metrics — and had no breakdown by
  model, date, or test category at all, despite §20 explicitly asking for
  it. All added.
- **§21**: `prompts/metadata.json`'s `evaluation_score` field was always
  `null`. `evaluation/runner.py` now writes the real measured score back
  after every run.
- **§24**: "unsupported operations" (asking the assistant to browse the
  live web, make phone calls, execute arbitrary code, etc.) wasn't a
  distinct guardrail check — it would have silently fallen through to a
  generic response. Added `detect_unsupported_operation`.
- **§25**: a recount found only 12 genuinely distinct injection test cases
  existed (8 dataset + 4 unit tests), short of the claimed 15. Added a new
  detection pattern (workspace-data exfiltration attempts) and 6 more unit
  tests to reach **18 total**, covering every example category the spec
  lists (override instructions, reveal hidden prompt, reveal API keys,
  ignore approval, unauthorized tools, extract private workspace info,
  direct + indirect).
- **§27**: "invalid tool arguments" and "unexpected output type" weren't
  checked at all. Added `validate_tool_arguments` (a small per-tool schema
  check) and `validate_output_type`.

All of this is covered by new tests: `tests/test_week6_logging_dashboard.py`
(7 tests) and `tests/test_week6_guardrails_extra.py` (11 tests), plus 6
additional injection-pattern tests appended to
`tests/test_week6_guardrails.py`.

## 9. Reliability, cost, and latency completeness audit (§29-37)

A follow-up audit against §29-37's exact checklists (mirroring the §19-28
audit in §8 above) found further gaps between documentation and actual
live wiring:

- **§31 Timeout Handling**: retrieval and model calls in `chat_routes.py`
  were only *traced*, never actually time-boxed — a hanging embedding
  search or model call could have frozen the request indefinitely despite
  `app.reliability.timeouts` existing as a library. Now wired in with real
  timeouts (retrieval 8s, model calls 20s per retry attempt, agent
  workflow steps 30s), and retrieval additionally degrades gracefully via
  `safe_retrieval` on either a timeout or a hard failure.
- **§32 Agent Loop Prevention**: `AgentLoopGuard.record_revision()` (max
  revision cycles) was unreachable dead code — nothing in the codebase
  ever called it, because the Meeting Agent is a single-turn tool-calling
  agent with no self-critique/revise loop. Documented this honestly in the
  class docstring and in `docs/WEEK6_RELIABILITY.md`, rather than forcing
  a fake wiring, matching the same scoping decision already made for
  multi-agent metrics.
- **§34 Cost Tracking**: "cost by model", "cost by agent", and "cost by
  feature" aggregations — explicitly required by the spec — didn't exist
  at all. Required adding an `agent_key` column to the `Trace` model
  (nothing previously tracked which agent a request belonged to) and new
  `cost_by_model`/`cost_by_agent`/`cost_by_feature` functions in
  `app/observability/cost.py`, now surfaced as three tables on the live
  dashboard.
- **§36 Latency Analysis**: only end-to-end latency was measured anywhere.
  Built `app/observability/latency_analysis.py` to break latency down by
  LLM/retrieval/tool stage from real `Trace`/`TraceStep` data (mean,
  median, P50, P95 each) and automatically identify the largest
  bottleneck. "Database latency" is honestly reported as **not
  separately measured** (this platform uses local SQLite with no
  per-statement instrumentation) rather than fabricated — see the `note`
  field in every latency report.

All of this is covered by 11 new tests in
`tests/test_week6_cost_latency.py`, plus updated dashboard-render
assertions in `tests/test_week6_logging_dashboard.py`. Full narrative
writeup for §29-33 (failure injection scenarios, retry classification
table, timeout configuration, loop-prevention controls, graceful
degradation): **`docs/WEEK6_RELIABILITY.md`**.

## 10. Experiments and failure-taxonomy completeness audit (§38-44)

A third follow-up audit (matching the pattern of §8 and §9) found two more
gaps between documentation and real measurement:

- **§38 Experiment 3 (Top-K)** and **Experiment 5 (Guardrails)** were
  narrated with "(estimated)" numbers rather than actually run. Built
  `evaluation/experiment_retrieval_topk.py` (seeds a real Flask/SQLite
  knowledge base and calls the real `embedding_service.semantic_search`)
  and `evaluation/experiment_guardrails.py` (calls the real
  `validate_input` against all 8 adversarial dataset cases). Running the
  guardrails experiment for real caught a genuine detection gap —
  3 of 8 adversarial phrasings weren't actually blocked (an
  environment-variable-phrased secret request, an elevated-authorization
  claim, and a "repeat everything above" exfiltration attempt) — which is
  exactly the kind of finding a narrated-but-never-run experiment cannot
  surface. All three patterns were added to
  `app.guardrails.input.INJECTION_PATTERNS`; the experiment now measures a
  real 8/8.
- **§40**: "every failed evaluation should receive a failure code" wasn't
  implemented — the F01-F14 taxonomy existed only as prose in
  `docs/WEEK6_FAILURE_TAXONOMY.md`. Built
  `evaluation/evaluators/failure_taxonomy.py`, wired into
  `evaluation/runner.py` so every `FAIL` result is automatically coded.
  Running it against the real baseline data caught that two of the
  earlier hand-written RCA codes (D06/D07, previously labeled F04) were
  imprecise — the automated classifier correctly identifies them as
  **F06 State Failure** instead, since the tool *arguments* actually
  matched the expected (deliberately invalid) value; the real failing
  check was `eval_recovery_behavior` not `eval_tool_arguments`. §41's RCA
  table has been corrected to match the automated classifier's output
  rather than the earlier manual guess.

Covered by 19 new tests: `tests/test_week6_experiments.py` (7) and
`tests/test_week6_failure_taxonomy.py` (12).

## Companion documents

- `docs/WEEK6_BASELINE.md` — Phase 1 baseline (§7)
- `docs/WEEK6_TASK_SUCCESS_DEFINITION.md` — exact success criteria + by-category results (§13)
- `docs/WEEK6_RAG_EVALUATION.md` — RAG metrics + failure classification (§14/§15)
- `docs/WEEK6_AGENT_EVALUATION.md` — agent evaluation results (§16)
- `docs/WEEK6_EXPERIMENTS.md` — all 7 required experiments (§38)
- `docs/WEEK6_FAILURE_TAXONOMY.md` — F01-F14 (§40)
- `docs/WEEK6_ROOT_CAUSE_ANALYSIS.md` — 10 failures analyzed, 6 of them real (§41)
- `docs/WEEK6_JUDGE_VS_HUMAN.md` — §12's required judge-vs-human comparison (11 cases)
- `docs/WEEK6_RELIABILITY.md` — failure injection, retry/timeout/loop-prevention decisions, graceful degradation (§29-33)
- `docs/WEEK6_SECURITY_REVIEW.md` — 12 risks, 2 genuinely fixed this week (§46)
- `docs/WEEK6_RELEASE_GATE.md` — release criteria (§44)
- `docs/WEEK6_PRODUCTION_READINESS.md` — 25->90/100 score (§45)
