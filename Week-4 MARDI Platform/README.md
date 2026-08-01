# MARDI — Multi-Agent Research and Decision Intelligence Platform

**Week 4 Submission** — A full-stack application: a **FastAPI backend**
running a LangGraph-based multi-agent workflow (Supervisor, Researcher,
Analyst, Critic, Writer), and a **React frontend** dashboard that consumes
it live — no mock data anywhere.

![Status](https://img.shields.io/badge/tests-57%2F57%20passing-brightgreen)
![Eval](https://img.shields.io/badge/eval%20scenarios-25%2F25-brightgreen)
![Requirements](https://img.shields.io/badge/requirements-19%2F19-brightgreen)

---

## Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [Technologies Used](#technologies-used)
- [Project Structure](#project-structure)
- [Installation & Quick Start](#installation--quick-start)
- [Configuration](#configuration)
- [Live Demo](#live-demo)
- [Verifying Everything Works](#verifying-everything-works)
- [Documentation Index](#documentation-index)
- [Documentation Gaps](#documentation-gaps)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Authors](#authors)
- [What Changed From the CLI-only Version](#what-changed-from-the-cli-only-version)

---

## Project Overview

MARDI takes a complex research or decision request (e.g. *"Compare three
cloud platforms for deploying an AI SaaS application"*) and, instead of
sending it to a single LLM call, routes it through a coordinated team of
five specialized agents built on **LangGraph**:

1. **Supervisor** — analyzes the request, asks clarifying questions if
   it's ambiguous, and builds a dynamic task plan.
2. **Researcher** (parallel, fan-out) — gathers evidence for each
   candidate option from a controlled local corpus.
3. **Analyst** — synthesizes the evidence into a structured comparison.
4. **Critic** — reviews the Analyst's output for gaps, unsupported claims,
   and quality issues, and can send it back for revision (bounded by a
   configurable cap).
5. **Writer** — produces the final, sourced report.

Two human-in-the-loop checkpoints (research plan approval and final
report review) sit in the workflow, and every step is exposed live to a
React dashboard via a FastAPI REST layer — so the same agent/graph code
that runs from the CLI also powers a full web application with zero
duplicated logic.

## Key Features

- **Five specialized agents** coordinated through a single shared,
  strongly-typed `WorkflowState` (LangGraph `StateGraph`), not raw chat
  history hand-offs.
- **Dynamic task planning** — the number and target of research tasks is
  derived from the request itself, not a fixed hard-coded sequence.
- **Parallel research execution** via LangGraph's `Send` fan-out/fan-in,
  with a matching timing evaluation (`evaluation/parallel_vs_sequential.py`).
- **Bounded quality-control loop** — Critic-requested revisions are capped
  by `max_revisions`, with both a unit test and an adversarial test
  proving the loop always terminates.
- **Two human-in-the-loop checkpoints** (plan approval, final review),
  implemented as an injectable callback so the same contract works for
  the CLI, tests, and the web API.
- **Live React dashboard** — Task Plan, Agent Pipeline, Evidence Store,
  Analysis & Critic Review, Execution Log, State Inspector, Final Report,
  and Analytics tabs, all polling real backend data.
- **Dual LLM provider support** — Google Gemini or Anthropic Claude,
  switchable via configuration, with a deterministic **mock LLM mode**
  that exercises the entire graph offline (no API key required).
- **Structured evidence and reporting** — every claim in the final report
  traces back to an evidence ID; nothing is fabricated when evidence is
  missing (the workflow fails cleanly instead).
- **Execution tracing and observability** — a structured, operational-only
  trace (no chain-of-thought) drives both the Execution Log tab and the
  Run History.
- **One-click deployment blueprint** (`render.yaml`) for Render, with a
  documented Railway alternative.

## Technologies Used

| Layer | Technology |
|---|---|
| Agent orchestration | [LangGraph](https://github.com/langchain-ai/langgraph), LangChain Core |
| Backend API | FastAPI, Uvicorn |
| Data validation | Pydantic |
| LLM providers | Google Gemini (`google-genai`) and/or Anthropic Claude (`anthropic`) |
| Backend testing | pytest |
| Frontend | React, Vite |
| Frontend charts | Recharts |
| Frontend icons | lucide-react |
| Deployment | Docker (backend), static hosting (frontend), Render Blueprint / Railway Procfile |

## Project Structure

```
mardi-platform/
├── backend/          FastAPI + LangGraph agents/tools/schemas — see backend/README.md
│   ├── app/
│   │   ├── main.py              # CLI entry point
│   │   ├── api.py                # FastAPI REST layer over the same graph
│   │   ├── config.py              # env-based settings
│   │   ├── agents/                 # supervisor, researcher, analyst, critic, writer
│   │   ├── graph/                   # state, workflow (LangGraph), routing, human checkpoints
│   │   ├── tools/                    # search, extraction, evidence store/retrieve, calculator
│   │   ├── schemas/                   # Task, Evidence, AnalysisOutput, CriticFeedback, FinalReport
│   │   ├── services/                   # LLM client (mock + live Gemini/Anthropic)
│   │   ├── storage/corpus/              # controlled local research corpus (JSON)
│   │   └── observability/                # execution tracer
│   ├── tests/                              # pytest — schemas, tools, routing, adversarial, full mock end-to-end
│   ├── evaluation/                          # scenario dataset, metrics, timing/quality experiments
│   ├── docs/                                 # architecture, specs, reviews, roadmap — see Documentation Index below
│   ├── .env.example
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/         React + Vite dashboard — see frontend/README.md
│   └── src/
│       ├── App.jsx                # top-level layout, tabs, polling orchestration
│       ├── api/client.js           # fetch wrapper for every backend endpoint
│       ├── hooks/usePolling.js      # generic interval-polling hook
│       └── components/               # Sidebar, RequestForm, AgentPipeline, TaskPlanTable, etc.
├── screenshots/      Captured screenshots of every dashboard tab
└── render.yaml       One-click deployment blueprint (Render)
```

## Installation & Quick Start

**Prerequisites:** Python 3.10+, Node.js (for the frontend), and either a
free [Gemini API key](https://aistudio.google.com) or an
[Anthropic API key](https://console.anthropic.com) if you want to run in
live mode. No key is required to run entirely offline against the
deterministic mock LLM.

**Terminal 1 — backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows; use `source venv/bin/activate` on Mac/Linux
pip install -r requirements.txt
copy .env.example .env         # Mac/Linux: cp .env.example .env
# edit .env: set GEMINI_API_KEY (or ANTHROPIC_API_KEY) — see backend/README.md
python -m uvicorn app.api:app --reload --port 8000
```

**Terminal 2 — frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Type a request, approve the two human
checkpoints as they appear, and watch every tab fill in with real data.

**CLI-only quick start** (no frontend needed — see `backend/README.md`
for full detail):
```bash
cd backend
pip install -r requirements.txt
python -m app.main --auto "Research the current open-source agent frameworks and recommend one for a small engineering team."
```

## Configuration

All backend configuration is environment-based (`backend/app/config.py`,
template at `backend/.env.example`) — no secrets are hard-coded anywhere.

| Variable | Purpose | Default |
|---|---|---|
| `LLM_PROVIDER` | `gemini` or `anthropic` | `gemini` |
| `GEMINI_API_KEY` | Gemini API key (live mode) | _(empty — falls back to mock)_ |
| `GEMINI_MODEL_NAME` | Gemini model name | `gemini-2.5-flash` |
| `ANTHROPIC_API_KEY` | Anthropic API key (live mode) | _(empty — falls back to mock)_ |
| `MODEL_NAME` | Anthropic model name | `claude-sonnet-5` |
| `LLM_MODE` | `auto` \| `mock` \| `live` | `auto` (live if the active provider's key is set, else mock) |
| `LLM_TIMEOUT_S` | Hard wall-clock cap per LLM call (seconds) | `30` |
| `MAX_REVISIONS` | Cap on the Analyst/Critic revision loop | `2` |
| `TOOL_MAX_RETRIES` | Retry budget for a failed live LLM call | `1` |
| `RESEARCH_CORPUS_PATH` | Path to the local research corpus | `app/storage/corpus` |
| `AUTO_APPROVE_CHECKPOINTS` | Auto-approve both human checkpoints (CI/demos) | `false` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `TRACE_DIR` | Directory for saved execution traces | `traces` |

The frontend reads its backend URL from `VITE_API_BASE` at build time
(`frontend/src/api/client.js`); in local dev, Vite's proxy forwards
`/api/*` to `http://127.0.0.1:8000` automatically, so no configuration is
needed to run both services locally.

## Live Demo

- **Deployment link:** _pending — see
  [`backend/docs/deployment.md`](backend/docs/deployment.md) for the
  ready-to-use Render Blueprint and step-by-step deploy instructions_
- **Demo video:** _pending — see
  [`backend/docs/demo_video_script.md`](backend/docs/demo_video_script.md)
  for the full recording script_

## Verifying Everything Works

```bash
cd backend
python -m pytest tests/ -v                    # 57 automated tests
python verify_requirements.py                 # 19/19 requirements checklist
python -m evaluation.evaluation_dataset       # 25/25 scenarios, real runs
python -m evaluation.evaluation_metrics       # 10 metrics vs. targets
python -m evaluation.experiment_1_single_vs_multi_agent
python -m evaluation.experiment_2_with_without_critic
python -m evaluation.parallel_vs_sequential
python -m evaluation.experiment_4_context_strategies
python -m evaluation.experiment_5_revision_limits
python -m pytest tests/test_adversarial.py -v # adversarial tests
```

## Documentation Index

Everything below lives in `backend/docs/` unless noted otherwise.

| Category | Document |
|---|---|
| **Architecture** | [`architecture_diagram.md`](backend/docs/architecture_diagram.md) · [`workflow_diagram.md`](backend/docs/workflow_diagram.md) · [Architecture section, `backend/README.md`](backend/README.md#architecture) |
| **API reference** | [Endpoint table, `backend/README.md`](backend/README.md#running-the-api-for-the-react-frontend) |
| **Setup / installation guide** | [Installation & Quick Start](#installation--quick-start) above · [`backend/README.md`](backend/README.md) · [`frontend/README.md`](frontend/README.md) |
| **Deployment guide** | [`deployment.md`](backend/docs/deployment.md) |
| **Testing** | [`backend/tests/`](backend/tests/) (automated suite — run `pytest tests/ -v`) · [`adversarial_testing.md`](backend/docs/adversarial_testing.md) |
| **Known limitations** | [`known_limitations.md`](backend/docs/known_limitations.md) |
| **Roadmap** | [`roadmap.md`](backend/docs/roadmap.md) |
| Agent specifications | [`agent_design_spec.md`](backend/docs/agent_design_spec.md) |
| State specification | [`workflow_state_spec.md`](backend/docs/workflow_state_spec.md) |
| Tool documentation | [`tool_documentation.md`](backend/docs/tool_documentation.md) |
| Tool permission boundaries | [`tool_permission_boundaries.md`](backend/docs/tool_permission_boundaries.md) |
| Handoff schemas | [`handoff_schemas.md`](backend/docs/handoff_schemas.md) |
| Context management | [`context_management.md`](backend/docs/context_management.md) |
| Evaluation dataset (25 scenarios) | [`evaluation_dataset.md`](backend/docs/evaluation_dataset.md) |
| Evaluation results/metrics | [`evaluation_metrics.md`](backend/docs/evaluation_metrics.md) |
| Experiment report (5 experiments) | [`1`](backend/docs/experiment_1_single_vs_multi_agent.md) · [`2`](backend/docs/experiment_2_with_without_critic.md) · [`3`](backend/docs/experiment_3_sequential_vs_parallel.md) · [`4`](backend/docs/experiment_4_context_strategies.md) · [`5`](backend/docs/experiment_5_revision_limits.md) |
| Security review | [`security_review.md`](backend/docs/security_review.md) |
| Builder journal | [`builder_journal.md`](backend/docs/builder_journal.md) |
| Demo video script | [`demo_video_script.md`](backend/docs/demo_video_script.md) |
| Screenshots | [`screenshots/`](screenshots/) |

## Documentation Gaps

In the interest of not inventing links to files that don't exist, the
following commonly-expected documents are **not currently present** in
this repository:

- **`CONTRIBUTING.md`** — no contribution guidelines exist yet.
- **`LICENSE`** — no license file is currently present in the repository;
  usage terms are unspecified.
- **Standalone `API.md`** — the API is documented as an endpoint table
  inside `backend/README.md` rather than as a separate file (linked
  above under Documentation Index).
- **Standalone `SETUP.md`** — setup instructions live in this README and
  in `backend/README.md` / `frontend/README.md` rather than a dedicated
  setup guide.
- **Standalone `TESTING.md`** — testing instructions and results are
  covered by the `backend/tests/` suite itself and
  `backend/docs/adversarial_testing.md`, rather than a single dedicated
  testing guide.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Frontend loads but requests never start | Confirm the backend is running on port 8000 (`python -m uvicorn app.api:app --reload --port 8000`) and reachable at `/api/health`. |
| `GET /api/health` shows `llm_mode: "mock"` when you expected live | `LLM_MODE=auto` resolves to mock unless the active provider's API key (`GEMINI_API_KEY` or `ANTHROPIC_API_KEY`, matching `LLM_PROVIDER`) is set in `.env`. |
| A run fails immediately with `error_count` > 0 and no task plan | Check the `error` field in `GET /api/runs/{id}/status` — this is typically a live LLM call returning malformed/truncated JSON on the request-analysis step; see `backend/docs/known_limitations.md` (LLM Provider Reliability). |
| Human checkpoint never appears / workflow seems stuck | Confirm `AUTO_APPROVE_CHECKPOINTS` is not unintentionally set to `true`, and check the backend logs for the run's thread — see `backend/app/api.py`'s `_run_graph`. |
| CORS errors in the browser console | In local dev, `frontend/vite.config.js` proxies `/api/*` to `http://127.0.0.1:8000`, so no CORS config is needed — make sure you're hitting `http://localhost:5173`, not the backend port directly. |
| `pip install` fails on `google-genai` or `anthropic` | Ensure you're on Python 3.10+ and using a fresh virtual environment (`python -m venv venv`), then re-run `pip install -r requirements.txt`. |
| Run history disappears after a redeploy | Expected — run state is in-memory only; see `backend/docs/known_limitations.md` (Deployment & Infrastructure). |

For anything not covered here, `backend/docs/known_limitations.md` and
`backend/docs/security_review.md` document every currently-known gap and
its severity.

## Contributing

No `CONTRIBUTING.md` currently exists in this repository (see
[Documentation Gaps](#documentation-gaps)). If you'd like to propose a
change, the existing test suite (`cd backend && pytest tests/ -v`) and
`verify_requirements.py` are the best starting points for confirming a
change doesn't regress existing behavior before submitting it.

## License

No `LICENSE` file is currently present in this repository (see
[Documentation Gaps](#documentation-gaps)) — usage terms are unspecified.

## Authors

Built by **Zahra**, Final Year BS Artificial Intelligence student at The
University of Faisalabad, Amin Campus, as part of the
**AI-Agent-Fellowship-2026** program (Track: AI Agents), under the
supervision of **Dr.Gufran Rana**.

## What Changed From the CLI-only Version

Nothing about the agents, graph, tools, or schemas changed between the
CLI-only build and this full-stack version — `backend/app/` is the same
LangGraph system throughout, now wrapped in `backend/app/api.py` (a
FastAPI layer) in addition to being invocable from `backend/app/main.py`
(the CLI still works — see `backend/README.md`).
