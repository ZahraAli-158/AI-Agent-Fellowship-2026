# AI Workspace Platform

A complete, self-hosted AI Workspace Platform — a simplified ChatGPT
Teams / Claude Projects — where multiple users create workspaces, configure
AI assistants, ground them in their own documents, give them persistent
memory, and reuse skills and prompts across projects.

Built for **Week 5 — AI Summer Internship 2026 (NLP & AI Agents track)**.

---

## 1. Problem Statement

Individual AI agents and single-session chat demos don't reflect how AI is
actually deployed in products and teams: real usage needs multiple users,
isolated workspaces, persistent history, grounding in private documents,
memory that survives across sessions, reusable prompts/skills, and basic
observability into usage and cost. This project builds that full platform
end-to-end — not another prompting exercise, but production-shaped AI
software with real authentication, a real database, and a real evaluation
suite.

## 2. Features

- **Authentication** — register / login / logout, bcrypt-hashed passwords,
  per-user isolated workspaces.
- **AI Workspaces** — create multiple workspaces (Marketing, Research,
  Programming, University, Business, Custom), each with its own
  conversations, documents, settings, and memory.
- **Assistant Configuration** — name, role, system prompt, model,
  temperature, max tokens, personality, response style — all editable per
  workspace.
- **Persistent Chat** — full conversation history with timestamps, session
  IDs, titles, in-sidebar search, delete, rename, and pin.
- **Knowledge Base** — upload PDF / DOCX / TXT / Markdown, automatic
  chunking + embedding, semantic search, per-document Q&A with citations.
- **Long-Term Memory** — the assistant remembers stated preferences, prior
  discussion topics, and manually pinned facts, across sessions.
- **Prompt Library** — save, edit, delete, and reuse prompts by category
  (Writing, Programming, Research, Business, Education, Custom).
- **AI Skills** — 10 reusable, one-click skills: Research, Summarization,
  Email, Report Generator, Meeting Notes Extractor, Idea Generator, Task
  Planner, SWOT Generator, Business Canvas Generator, Code Reviewer.
- **Document Intelligence** — upload → chunk → embed → search → cite →
  summarize → question-answer, all per document.
- **Workspace Dashboard** — conversations, documents, memory items, prompt
  templates, token usage, estimated cost, average latency, recent activity
  feed.
- **Advanced features implemented** (4+ required): Dark/Light mode toggle,
  Conversation Export (Markdown + PDF), Conversation Search, Pinned
  Conversations & Messages.

## 3. Technology Stack

| Layer | Choice |
|---|---|
| Backend | Python, Flask, Flask-SQLAlchemy, Flask-Login, Flask-Bcrypt |
| Frontend | Server-rendered Jinja2 + vanilla JS (fetch-based AJAX), hand-written CSS |
| Database | SQLite (default) — PostgreSQL / Supabase via `DATABASE_URL` |
| AI | Google Gemini (`google-generativeai`) — **gemini-3.6-flash** (default chat model) + **gemini-embedding-001** (embeddings), with an offline stub fallback |
| Search | Gemini embeddings (primary) → scikit-learn TF-IDF + cosine similarity (fallback) |
| Document parsing | `pypdf`, `python-docx` |
| PDF export | `reportlab` |
| Testing | `pytest` (40 tests) |
| Version control | Git / GitHub |

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full layered
architecture and design rationale, and
[`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) for the complete
schema.

## 4. Architecture (summary)

```
User → Frontend (Flask/Jinja2 + JS) → Backend API (Flask blueprints)
     → Authentication (Flask-Login) → Workspace Manager → Conversation Manager
     → AI Agent (Gemini) → Memory (MemoryItem table) → Knowledge Base (Chunk + embeddings)
     → LLM (Gemini, offline stub fallback) → Database (SQLAlchemy / SQLite)
```

Full diagram and request-lifecycle walkthrough in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 5. Installation

```bash
# 1. Clone / unzip the project, then from the "technical" folder:
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# then edit .env and set GEMINI_API_KEY (get one at https://aistudio.google.com/apikey)

# 4. Run
python run.py
# App runs at http://localhost:5000
```

The platform runs fully **without** a Gemini key too — it falls back to a
clearly-labeled offline stub for chat and to TF-IDF search for the
knowledge base, so every feature stays testable and demoable at zero API
cost. Add a real `GEMINI_API_KEY` to `.env` at any time to switch to live
responses — no restart-time code changes needed.

### Running the tests / evaluation / experiments

```bash
python -m pytest tests/ -v              # 40 automated tests
python evaluation/eval_runner.py        # 28 automated evaluation scenarios
python experiments/run_experiments.py   # 5 automated experiments
```

## 6. Deployment

The app is a standard Flask app (`run.py` / `app:create_app`) and deploys
cleanly to any of the platforms suggested in the brief:

- **Render / Railway**: set the start command to
  `gunicorn "app:create_app()"` (add `gunicorn` to `requirements.txt` for
  production), set `GEMINI_API_KEY`, `SECRET_KEY`, and `DATABASE_URL` as
  environment variables in the dashboard.
- **Hugging Face Spaces**: use the Docker SDK with a small Dockerfile that
  `pip install -r requirements.txt` then runs `python run.py` on
  `$PORT`.

**Environment variables required in production:**

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session signing — set to a long random string |
| `GEMINI_API_KEY` | Enables live chat + embeddings (optional — offline stub otherwise) |
| `DATABASE_URL` | e.g. a Supabase/PostgreSQL connection string for production |

**Known limitations** (see also §10):
- No live deployment URL is included in this deliverable — the app is
  fully local-run/deploy-ready but was not pushed to a public host.
- Chunk embeddings are computed serially at upload time; very large
  documents (100+ pages) will have a slower upload response.

## 7. API / Route Reference

All routes are server-rendered pages unless marked **(JSON)**.

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/register`, `/login` | Auth |
| GET | `/logout` | Auth |
| GET | `/workspaces/` | List workspaces |
| POST | `/workspaces/create` | Create workspace |
| GET | `/workspaces/<id>` | Workspace detail (conversations + settings) |
| POST | `/workspaces/<id>/settings` | Update assistant configuration |
| POST | `/workspaces/<id>/delete` | Delete workspace |
| POST | `/workspaces/<id>/chat/new` | New conversation |
| GET | `/workspaces/<id>/chat/<cid>` | Open conversation |
| POST | `/workspaces/<id>/chat/<cid>/send` **(JSON)** | Send a chat message (RAG + memory) |
| POST | `/workspaces/<id>/chat/<cid>/rename` \| `/pin` \| `/delete` | Conversation management |
| GET | `/workspaces/<id>/chat/<cid>/export?format=markdown\|pdf` | Export conversation |
| GET | `/workspaces/<id>/chat/search?q=` **(JSON)** | Search conversations |
| GET | `/workspaces/<id>/knowledge/` | Knowledge base UI |
| POST | `/workspaces/<id>/knowledge/upload` | Upload + chunk + embed a document |
| POST | `/workspaces/<id>/knowledge/<did>/delete` | Delete a document |
| GET | `/workspaces/<id>/knowledge/search?q=` **(JSON)** | Semantic search |
| POST | `/workspaces/<id>/knowledge/<did>/ask` **(JSON)** | Document-scoped Q&A |
| GET | `/workspaces/<id>/prompts/` | Prompt library UI |
| POST | `/workspaces/<id>/prompts/create` \| `/<pid>/edit` \| `/<pid>/delete` \| `/<pid>/use` | Prompt CRUD |
| GET | `/workspaces/<id>/skills/` | Skills UI |
| POST | `/workspaces/<id>/skills/<sid>/run` **(JSON)** | Run a skill |
| GET | `/workspaces/<id>/dashboard/` | Usage dashboard |
| POST | `/workspaces/<id>/dashboard/memory/add` \| `/<mid>/pin` \| `/<mid>/delete` **(JSON)** | Memory management |

## 8. Database

Full schema (12 tables, cascade rules, and rationale for the Chunk/Embedding
design) in [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md).

## 9. Screenshots

This text-only deliverable doesn't include rendered screenshots — run
`python run.py` and visit `http://localhost:5000` to see the live UI
(animated particle background, glassmorphism cards, dark/light themes,
ChatGPT-Teams-style sidebar layout).

## 10. Evaluation Results

Full 40-scenario framework: [`evaluation/eval_scenarios.md`](evaluation/eval_scenarios.md).
Automated subset result (`python evaluation/eval_runner.py`):

```
EVALUATION SUMMARY: 28/28 automated scenarios passed (100.0%)
Average measured latency: ~10ms across 12 timed calls (offline-stub mode)
```

The remaining scenarios in the 40-item framework are marked `[manual]` —
they require human judgment of generative quality (e.g. "does the SWOT
output cover all four quadrants meaningfully") and are documented as a
checklist rather than a boolean assertion, which is standard practice for
evaluating open-ended LLM output.

**Test suite:** `python -m pytest tests/ -v` → **40/40 passed** (auth,
workspace isolation, conversations, memory, prompt library, document
upload, semantic search, skill execution, database cascades, and
cross-user API security).

**Experiments:** `python experiments/run_experiments.py` — see
[`experiments/experiments.md`](experiments/experiments.md) for full write-up
and measured results (memory token overhead, prompt-detail effects, context
window growth/plateau at the 20-message cap, and chunk-size vs. relevance
trade-offs).

## 11. Future Improvements

- Swap the character-based chunker for a sentence/paragraph-aware splitter
  to reduce mid-sentence cuts at small chunk sizes (see Experiment 6).
- Stream chat responses token-by-token instead of returning the full
  message at once.
- Add role-based access control for shared/team workspaces (currently
  single-owner per workspace).
- Replace the rule-based memory extraction (`memory_service.py`) with an
  LLM-based extraction pass for higher-recall preference detection.
- Add real usage charts (token/cost over time) to the dashboard instead of
  point-in-time totals.
- Live deployment to Render/Railway with a public URL and CI-run test
  suite on every push.

---

## Project Structure

```
technical/
├── app/
│   ├── __init__.py            # Flask app factory
│   ├── models/models.py       # SQLAlchemy models (12 tables)
│   ├── routes/                # Blueprints: auth, workspace, chat, knowledge, prompt, skill, dashboard
│   ├── services/               # gemini, embedding, document, memory, skill, log services
│   ├── templates/              # Jinja2 templates
│   └── static/css, static/js   # Design system + interactive background + page scripts
├── tests/                      # 40 pytest tests
├── evaluation/                 # 40-scenario framework + automated runner
├── experiments/                # 6 experiments (5 automated) + write-up
├── docs/                       # Architecture + database schema docs
├── config.py                   # Central configuration
├── run.py                      # Entry point
├── requirements.txt
└── .env.example
```

---

## 12. Week 6 — Reliability & Observability Layer

Week 6 turns this platform from a demo into a measured, guarded, and
observable system. Full detail: **`docs/WEEK6_REPORT.md`** (start there),
plus `docs/WEEK6_BASELINE.md`, `WEEK6_TASK_SUCCESS_DEFINITION.md`,
`WEEK6_RAG_EVALUATION.md`, `WEEK6_AGENT_EVALUATION.md`,
`WEEK6_EXPERIMENTS.md`, `WEEK6_FAILURE_TAXONOMY.md`,
`WEEK6_ROOT_CAUSE_ANALYSIS.md`, `WEEK6_JUDGE_VS_HUMAN.md`,
`WEEK6_SECURITY_REVIEW.md`, `WEEK6_RELEASE_GATE.md`, and
`WEEK6_PRODUCTION_READINESS.md`.

**Highlights:**
- 62-case evaluation dataset across 6 categories (`evaluation/dataset.jsonl`)
- Deterministic evaluators + RAG evaluators + agent evaluators + LLM-as-judge (`evaluation/evaluators/`, `evaluation/judge.py`)
- One-command evaluation pipeline + regression testing: `python -m evaluation.runner --label <name> --prompt-version v3` / `python -m evaluation.regression baseline_v1 agent-system-v3`
- Execution tracing (per pipeline stage, incl. one step per tool call) + trace viewer + quality dashboard at `/observability/`
- Input/output guardrails incl. direct + indirect prompt-injection defense (`app/guardrails/`)
- Tool risk classification (L0–L4) with an approval gate **enforced in the live agent tool path**, not just documented (`app/guardrails/permissions.py`, wired into `app/services/agent_service.py`)
- Retries, timeouts, agent loop prevention, graceful degradation (`app/reliability/`)
- Cost + latency tracking (`app/observability/cost.py`, `metrics.py`)
- Prompt versioning (v1→v3) with measured improvement: **91.94% → 100% task success, 0 regressions**
- RAG evaluation: 100% retrieval hit rate / context relevance / citation correctness on `agent-system-v3`
- Production readiness score: **25/100 → 90/100**
- 156 new automated tests (218 total in the project), all passing: `python -m pytest tests/ -q`

Run the evaluation suite:
```bash
python -m evaluation.runner --label baseline_v1 --prompt-version v1
python -m evaluation.runner --label agent-system-v3 --prompt-version v3
python -m evaluation.regression baseline_v1 agent-system-v3
```
