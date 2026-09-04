# Architecture

## Layered request flow

```
Browser (HTML/CSS/JS, no framework — vanilla fetch() for AJAX)
   │
Flask routes (blueprints, one per module)
   │  auth_routes · workspace_routes · chat_routes · knowledge_routes
   │  prompt_routes · skill_routes · dashboard_routes
   │
Services (business logic, framework-agnostic)
   │  gemini_service    — LLM chat + embeddings, offline stub fallback
   │  embedding_service — semantic search (Gemini embeddings → TF-IDF fallback)
   │  document_service  — text extraction (pypdf/docx) + chunking
   │  memory_service     — long-term memory extraction/recall
   │  skill_service      — the 10 reusable AI skills
   │  log_service        — observability/cost logging
   │
Models (SQLAlchemy ORM) ── db.session
   │
Database (SQLite by default; PostgreSQL/Supabase via DATABASE_URL)
```

Each module in the spec's Platform Architecture diagram maps 1:1 to a
Flask blueprint + its own template folder slice + (where relevant) a
dedicated service file — so any module can be read, tested, or replaced in
isolation.

## Why these choices

- **Flask over FastAPI**: the brief allows either; Flask's server-rendered
  Jinja2 templates + a thin AJAX layer let one person ship a complete,
  cohesive UI (chat, knowledge base, dashboard) faster than wiring a
  separate SPA frontend to a JSON API, while still exposing clean JSON
  endpoints (`/chat/.../send`, `/knowledge/.../search`, `/skills/.../run`)
  for anything that needs to be async.
- **SQLite by default**: zero-config for local development and grading;
  `DATABASE_URL` swaps to PostgreSQL/Supabase for production with no code
  changes, since everything goes through SQLAlchemy.
- **Gemini with an offline stub**: `gemini_service.py` never raises if
  `GEMINI_API_KEY` is missing — it returns a clearly-labeled stub response
  instead. This keeps the entire platform (and its automated tests/evals)
  runnable and deterministic with zero API cost, while working normally the
  moment a real key is added to `.env`.
- **Embeddings with a TF-IDF fallback**: chunks get real Gemini embeddings
  when a key is configured; `embedding_service.py` falls back to
  scikit-learn TF-IDF + cosine similarity when they're not, so the
  Knowledge Base module is never a dead feature in offline/demo mode.
- **Memory as its own table, not conversation history**: `MemoryItem` rows
  are workspace-scoped and independent of any single conversation, so
  preferences survive across sessions at a small, bounded token cost
  (top-N pinned/weighted facts), instead of requiring ever-growing chat
  history to be replayed.

## Request lifecycle: sending a chat message

1. Browser posts to `/workspaces/<id>/chat/<id>/send` via `fetch()`.
2. Route stores the user `Message`, updates the conversation title if it's
   the first message.
3. `memory_service` scans the message for memorable statements and updates
   `MemoryItem` rows (frequency-weighted); relevant memory is compiled into
   a context block.
4. If "Use knowledge base" is checked, `embedding_service.semantic_search`
   retrieves the top-matching `Chunk`s across the workspace's `Document`s
   and builds a citation-annotated context block.
5. Both context blocks are appended to the workspace's configured
   `system_prompt`, along with assistant name/role/personality/style.
6. `gemini_service.chat_completion` is called with the last 20 turns of
   history, the augmented system prompt, and the workspace's model/
   temperature/max_tokens.
7. The assistant `Message` is stored (with citations as JSON), a `Log` row
   captures tokens/latency for the dashboard, and the JSON response is
   returned to the browser for inline rendering.

## Security notes

- Passwords are hashed with bcrypt (`Flask-Bcrypt`), never stored in plain
  text.
- Every workspace-scoped route calls `get_owned_workspace_or_404`, which
  404s on a nonexistent workspace and 403s if the current user doesn't own
  it — verified in `tests/test_workspace.py`,
  `tests/test_api.py::test_cross_user_access_forbidden`, and
  Evaluation Scenario 38.
- Prompt template mutations check `template.user_id == current_user.id`
  before allowing edit/delete — verified in
  `tests/test_prompts.py` and Evaluation Scenario 29.
- File uploads are restricted by extension (`ALLOWED_EXTENSIONS`) and size
  (`MAX_CONTENT_LENGTH`), and stored under a per-workspace, UUID-prefixed
  path to avoid collisions and directory traversal via user-controlled
  filenames (`secure_filename` from Werkzeug).
