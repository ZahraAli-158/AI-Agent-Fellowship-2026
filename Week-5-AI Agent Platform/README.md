# AI Workspace Platform

A multi-user AI Workspace Platform (similar to ChatGPT Teams / Claude Projects) built as a university
capstone project. FastAPI backend, Streamlit frontend, SQLite (PostgreSQL-compatible), supporting
Gemini, OpenAI, and Anthropic as pluggable LLM providers with a guaranteed offline fallback.

![Architecture Diagram](docs/diagrams/architecture_diagram.svg)

## Quick Start

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add at least one provider API key
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501, register an account, create a workspace, and start chatting.
Without any API key configured, every feature still works end-to-end using the built-in Mock Provider.

## Project Structure

```
ai-workspace-platform/
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI routers (auth, workspaces, assistants, conversations, ...)
│   │   ├── core/               # config, security, rate limiting, model registry
│   │   ├── db/                  # SQLAlchemy session/engine
│   │   ├── models/              # 12 SQLAlchemy models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── llm/             # Provider Factory + Gemini/OpenAI/Anthropic/Mock providers
│   │   │   ├── knowledge/       # RAG: extractors, chunker, embeddings, semantic search
│   │   │   └── chat_service.py  # chat orchestration + memory recall injection
│   │   ├── skills/               # 10 reusable AI skills registry
│   │   └── main.py
│   ├── tests/                    # 51 pytest tests
│   ├── requirements.txt
│   ├── Dockerfile
│   └── render.yaml
├── frontend/
│   ├── app.py                    # Login/Register + workspace management shell
│   ├── nav.py                    # shared sidebar navigation
│   ├── theme.py                  # purple glassmorphism theme + dark/light persistence
│   ├── components.py             # reusable glass-card UI components
│   ├── api_client.py
│   ├── pages/                    # Dashboard, Chat, Knowledge Base, Memory, Prompt Library, AI Skills, Assistant Settings
│   ├── requirements.txt
│   └── Dockerfile
├── docs/
│   ├── 1_Architecture_Documentation.docx
│   ├── 2_Research_Report.docx
│   ├── 3_Evaluation_Framework.docx
│   ├── 4_Experiments.docx
│   ├── 5_Security_Review.docx
│   ├── 6_Performance_Analysis.docx
│   ├── 7_Deployment_Guide.docx
│   ├── BUILDER_JOURNAL.md         # honest development log: decisions, bugs found & fixed
│   ├── diagrams/                  # architecture diagram + database ERD (SVG)
│   ├── api/                       # OpenAPI spec + generated API_DOCUMENTATION.md
│   ├── evaluation/                # evaluation_dataset.json + evaluation_results.md
│   └── screenshots/                # see screenshots/README.md — add your own captures here
├── docker-compose.yml
└── README.md
```

## Running Tests

```bash
cd backend
pytest tests/ -v
```

**51/51 tests passing**, covering auth, workspaces, assistants, chat, documents/RAG, memory, prompts,
skills, dashboard, export, workspace sharing/clone/archive, message pinning, and the LLM provider
factory (including the mock-fallback bug fix and the memory-recall-in-chat fix).

## Documentation

| Document | Location |
|---|---|
| Architecture Documentation | `docs/1_Architecture_Documentation.docx` + `docs/diagrams/architecture_diagram.svg` |
| Database ERD | `docs/diagrams/database_erd.svg` |
| Research Report | `docs/2_Research_Report.docx` |
| API Documentation | `docs/api/API_DOCUMENTATION.md` (48 endpoints, generated from the live OpenAPI schema) + `docs/api/openapi.json` |
| Evaluation Dataset | `docs/evaluation/evaluation_dataset.json` (44 scenarios) |
| Evaluation Results | `docs/evaluation/evaluation_results.md` (real pytest run against the dataset) |
| Experiments | `docs/4_Experiments.docx` |
| Security Review | `docs/5_Security_Review.docx` |
| Performance Report | `docs/6_Performance_Analysis.docx` |
| Builder Journal | `docs/BUILDER_JOURNAL.md` |
| Screenshots | `docs/screenshots/` (see its `README.md` — needs to be captured locally, see below) |
| Deployment Guide | `docs/7_Deployment_Guide.docx` |

All `.docx` files are formatted Times New Roman, Heading 14pt Bold, Body 12pt, with table of contents
and page numbers.

With the backend running locally, the interactive API docs are also live at
`http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`.

## Screenshots & Demo Video

Not included as static files in this repo — capturing them requires a real browser against the
running app. `docs/screenshots/README.md` has the exact list and filenames to capture (Win+Shift+S
works fine) before pushing to GitHub. For a demo video, a 2–3 minute screen recording (OBS Studio,
Xbox Game Bar, or Loom) walking through: register → create workspace → configure assistant → chat →
upload a document → ask a grounded question → run an AI skill → check the dashboard, covers the core
flow well.

## Deployment

Not yet deployed to a live URL — this requires your own hosting accounts/credentials.
See `docs/7_Deployment_Guide.docx` for exact manual steps to publish to GitHub and deploy via Render
(backend) + Streamlit Community Cloud (frontend), or self-host via `docker compose up --build`.

## Pushing to GitHub

```bash
cd ai-workspace-platform
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

`.gitignore` already excludes `.env`, `*.db`, `uploads/`, and `vector_store/` — never commit real API keys.
