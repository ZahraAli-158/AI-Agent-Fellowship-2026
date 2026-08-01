# MARDI — Multi-Agent Research and Decision Intelligence Platform

A LangGraph-based multi-agent system that coordinates five specialized
agents (Supervisor, Researcher, Analyst, Critic, Writer) to turn a complex
research/decision request into a validated, sourced final report — instead
of sending the whole request to one LLM call.

## Running the API (for the React frontend)

```bash
python -m uvicorn app.api:app --reload --port 8000
```

This is a thin REST layer (`app/api.py`) over the exact same agents/graph/
tools used by the CLI — nothing in `app/agents`, `app/graph`, `app/tools`,
or `app/schemas` changed to support it. Each run executes on its own
background thread; human checkpoints block that thread on a
`threading.Event` until the frontend resolves them via POST, reusing the
same `app/graph/human.py` callback contract the CLI already used.

| Method & Path | Purpose |
|---|---|
| `POST /api/requests/analyze` | Request Analysis preview (Requirement 1) — runs just the Supervisor's analysis step |
| `POST /api/runs` | Workflow Execution — starts a new run, returns `run_id` |
| `GET /api/runs/{id}/status` | Live Workflow Status — workflow status, checkpoint states, pending checkpoint |
| `GET /api/runs/{id}/tasks` | Task Plan — with live per-task status |
| `GET /api/runs/{id}/evidence` | Evidence — full store + aggregate summary |
| `GET /api/runs/{id}/trace` | Execution Logs — structured trace + run summary |
| `GET /api/runs/{id}/report` | Final Report — structured + markdown |
| `GET`/`POST /api/runs/{id}/checkpoint` | Human Checkpoint Approvals |
| `GET /api/runs/{id}/state` | Workflow State — full raw state for the State Inspector |
| `GET /api/runs` | Run History |
| `GET /api/health` | Health check + active LLM provider/mode |

## Quick start (CLI, still works)

```bash
pip install -r requirements.txt
cp .env.example .env          # add GEMINI_API_KEY (free, no card needed) to run in "live" mode

# Runs entirely offline against a deterministic mock LLM + local corpus —
# no API key needed:
python -m app.main --auto "Research the current open-source agent frameworks and recommend one for a small engineering team."

# Interactive (prompts you at both human checkpoints):
python -m app.main "Compare three cloud platforms for deploying an AI SaaS application."

# Tests
pytest tests/ -v

# Parallel vs sequential timing evaluation
python -m evaluation.parallel_vs_sequential
```

The assignment does not mandate a specific LLM provider (only the
orchestration framework, LangGraph) — so `app/services/llm_client.py`
supports both **Google Gemini** (default; get a free key at
[aistudio.google.com](https://aistudio.google.com), no credit card or phone
verification needed) and **Anthropic Claude** (get a key at
[console.anthropic.com](https://console.anthropic.com); new accounts get a
small one-time free trial credit). Set `LLM_PROVIDER=gemini` or
`LLM_PROVIDER=anthropic` in `.env`, plus the matching API key, and
`LLM_MODE=auto` (or leave it — that's the default) to switch from mock to
live automatically once a key is present.

## Why LangGraph

This project needs (a) a real, bounded revision **cycle**, (b) a **parallel
fan-out/fan-in** over independent research tasks, and (c) one shared,
strongly-typed state object read/written by five different agents.
LangGraph's `StateGraph` + `Send` primitives map onto exactly that; a plain
linear chain (or CrewAI's simpler sequential/hierarchical process model)
would need extra hand-rolled bookkeeping to express the same cycle and
fan-out safely.

## Architecture

```
analyze_request -> (clarify?) -> create_plan -> checkpoint_1 (human)
  -> [researcher x N, parallel via Send] -> analyst -> critic -> decide_after_critic
       -> revision needed & under cap -> analyst   (loop)
       -> approved / cap reached      -> writer -> checkpoint_2 (human)
            -> approved         -> finalize -> END
            -> request changes  -> analyst  (loop, same cap)
```

See `app/graph/workflow.py` for the exact node/edge wiring and the
docstring explaining state maintenance, agent communication, handoffs,
loop control, and failure handling — all in one place, as required.

## Where each requirement lives

| Requirement | Where |
|---|---|
| 5 specialized agents | `app/agents/*.py` |
| Request analysis / clarification / dynamic planning | `app/agents/supervisor.py` |
| Agent specialization + tool boundaries | `docs/agent_design_spec.md`, `docs/tool_permission_boundaries.md` |
| Research tools | `app/tools/*.py` |
| Evidence model | `app/schemas/evidence.py` |
| Shared state | `app/graph/state.py`, `docs/workflow_state_spec.md` |
| Handoff contracts | `docs/handoff_schemas.md` |
| Quality-control loop (capped) | `app/graph/routing.py::route_after_critic_decision`, `app/agents/supervisor.py::decide_after_critic` |
| Parallel execution | `app/graph/routing.py::dispatch_research`, `evaluation/parallel_vs_sequential.py` |
| Human-in-the-loop | `app/graph/human.py` |
| Context management | `docs/context_management.md` |
| Failure handling | error branches in every `app/agents/*.py` node + `app/services/llm_client.py` retry |
| Execution tracing | `app/observability/tracer.py` |
| Dashboard | separate React app (see `agent-dashboard.jsx`) — this repo produces the JSON/markdown data it would consume |
| Final report | `app/schemas/reports.py::FinalReport.to_markdown()` |

## A note on Human-in-the-Loop implementation

Rather than using LangGraph's native `interrupt()` + checkpointer (which
requires a persistence backend and changes shape across LangGraph
versions), checkpoints are plain graph nodes that call an injectable
`human_review_callback(checkpoint_name, payload) -> dict`
(`app/graph/human.py`). `cli_callback` prompts on stdin for the CLI demo;
`auto_approve_callback` is used in tests/CI. Swapping in real `interrupt()`
based pause/resume for a production web UI would mean replacing these two
callbacks with `interrupt(payload)` calls and adding a checkpointer to
`build_workflow()` — the rest of the graph is unaffected.

## Project structure

```
multi-agent-platform/
├── app/
│   ├── main.py                 # CLI entry point
│   ├── config.py               # env-based settings
│   ├── agents/                 # supervisor, researcher, analyst, critic, writer
│   ├── graph/                  # state, workflow (LangGraph), routing, human checkpoints
│   ├── tools/                  # search, extraction, evidence store/retrieve, calculator
│   ├── schemas/                # Task, Evidence, AnalysisOutput, CriticFeedback, FinalReport
│   ├── services/                # LLM client (mock + live Anthropic)
│   ├── storage/corpus/          # controlled local research corpus (JSON)
│   └── observability/           # execution tracer
├── tests/                       # pytest — schemas, tools, routing, full mock end-to-end
├── evaluation/                  # parallel vs sequential timing
├── docs/                        # agent spec, state spec, handoffs, context mgmt, tool perms
├── .env.example
├── requirements.txt
├── Dockerfile
└── README.md
```

## Known limitations

Summary (see [`docs/known_limitations.md`](docs/known_limitations.md) for
the full consolidated list, organized by category):

- The local corpus is small and illustrative (agent frameworks, cloud
  platforms) — real deployments would swap `app/tools/search.py` for a
  live web-search/RAG backend without touching any agent or graph code.
- The Critic reviews the Analyst's structured output, not the raw source
  documents directly (see `docs/context_management.md`).
- Live-mode token-usage tracking is stubbed but not wired to a real
  Anthropic response's `usage` field (see `docs/context_management.md`'s
  last section).
