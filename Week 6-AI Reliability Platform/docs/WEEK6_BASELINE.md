# Week 6 — Phase 1: Baseline (Baseline V1)

This documents the state of the Week 5 **AI Workspace Platform** *before* any
Week 6 reliability/observability work was applied, per §7 of the Week 6 spec.
Foundation project: **Week 5 — AI Workspace Platform** (Flask, Gemini API,
workspaces, chat, knowledge base/RAG, agents, prompt library, usage
dashboard).

## System configuration at baseline

| Field | Value |
|---|---|
| Model | `gemini-3.6-flash` (configurable per workspace; falls back to an offline deterministic stub when `GEMINI_API_KEY` is unset) |
| Model parameters | `temperature` per workspace (default 0.7), `max_tokens` per workspace (default 1024) |
| System prompt version | Single, unversioned prompt assembled from `workspace.system_prompt` + assistant name/role/personality/response style. No history, no explicit grounding/ambiguity/injection guidance. This is now frozen as `prompts/v1.txt`. |
| RAG configuration | ChromaDB-style chunking with a scikit-learn TF-IDF/embedding fallback (`app/services/embedding_service.py`), top-k = 4, no citation validation, no groundedness check |
| Tool definitions | Meeting Agent tools (`create_task`, `list_tasks`, `update_task`, `complete_task`, `delete_task`, `email_task_summary`, `search_knowledge_base`) with **no risk classification and no approval gate** — every tool could execute directly if the model chose to call it |
| Agent configuration | Iterative function-calling loop with **no step limit, no duplicate-call detection, no revision cap** |

## Baseline metrics (measured via `evaluation/runner.py --label baseline_v1 --prompt-version v1`)

| Metric | Value |
|---|---|
| Total test cases | 62 |
| Task success rate | **91.94%** (57/62) |
| Avg. judge score | 3.26 / 5 (offline heuristic judge — see `evaluation/judge.py` limitations) |
| Tool selection accuracy | 100% (10/10 Category D cases) |
| Avg. latency | ~0 ms (offline rule-based baseline harness; see "Known limitation" below) |
| Avg. token usage | 57.2 tokens/request (30.9 input, 26.3 output — measured directly from `reports/baseline_v1.json`) |
| P95 latency | ~0 ms (offline) |
| Estimated cost | $0.000639 total across 62 cases |

**Known limitation of this baseline measurement:** before Week 6, there was
no evaluation harness at all — these numbers are only obtainable *because*
Week 6's `evaluation/runner.py` + `evaluation/dataset.jsonl` now exist. The
number itself (91.94%) is measured by running the **offline rule-based
system-under-test** (`evaluation/system_under_test.py`), which stands in for
a live Gemini call so the suite is runnable without an API key. When run
with `--mode live` against a configured Gemini key, latency and cost become
real end-to-end numbers (typically 500–2000ms and a few thousandths of a
cent per call for `gemini-3.6-flash`), while the pass/fail logic itself is
unchanged. See `docs/WEEK6_TASK_SUCCESS_DEFINITION.md` for the exact
pass/fail criteria (this baseline number reflects the deterministic tool
checks *and* the agent-specific evaluators from `docs/WEEK6_AGENT_EVALUATION.md`,
not tool-selection alone).

## Known failure cases at baseline (pre-improvement)

1. **B04** — a conditional request ("create X only if condition, otherwise
   list") is handled by always creating first instead of checking the
   condition (branching) first.
2. **B07** — a recurring/bulk request ("a task for every Monday in
   September") is not recognized as a task-creation intent at all.
3. **D03** — a knowledge-base search's tool argument (`query`) is populated
   with the entire raw utterance instead of just the topic phrase, making
   downstream argument-accuracy checks fail even though the correct tool was
   selected.
4. **D06** — a quoted date phrase ("'45th of Marchtember'") in an
   `update_task` request is mis-extracted as a task *title* instead of
   being recognized as the (invalid) due-date value the user actually gave.
5. **D07** — an invalid, non-numeric task ID (`'abc'`) is passed straight
   through to `complete_task` instead of the system asking for a valid ID.

All five are fixed by `agent-system-v3` (100% task success, 0 remaining
failures) — see `docs/WEEK6_ROOT_CAUSE_ANALYSIS.md` for the fix for each.
A sixth issue (not a *dataset* failure, but a real bug caught by the new
RAG evaluator) is documented in `docs/WEEK6_RAG_EVALUATION.md`: the offline
retrieval stand-in briefly hallucinated an Eiffel-Tower answer to an
unrelated Statue-of-Liberty question (E02) due to an overly broad retrieval
fallback — also fixed.

See `docs/WEEK6_ROOT_CAUSE_ANALYSIS.md` for the full root-cause analysis and
fixes (two of these three are fixed by the v2/v3 prompt+routing
improvements; see `docs/WEEK6_EXPERIMENTS.md` Experiment 1).

## Filled evaluation dataset (§9)

`evaluation/runner.py` now writes the dataset back out with every case's
`actual_result`, `score`, `pass_fail`, and `notes` populated, in both JSONL
and CSV, per §9's schema:
- `reports/baseline_v1_filled_dataset.jsonl` / `.csv`
- `reports/agent-system-v2_filled_dataset.jsonl` / `.csv`
- `reports/agent-system-v3_filled_dataset.jsonl` / `.csv`

No optimization was performed before this baseline was recorded, per §7.
