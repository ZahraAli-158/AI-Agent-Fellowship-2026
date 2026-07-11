# Enterprise Document Intelligence Platform

A Retrieval-Augmented Generation (RAG) application for uploading multiple
documents and having a natural-language conversation with them — built with
Streamlit, ChromaDB, and Google's Gemini API.

## Features

| Feature | Description |
|----------|-------------|
| **User Authentication** | Simulated login/register (accounts persisted locally in `data/users.json`, password hashed) + guest mode — demo-grade, not production security |
| **Multi-document Upload** | Supports PDF, TXT, Markdown, and **DOCX** |
| **Document Processing** | Extraction, cleaning, chunking; shows pages, chunks, and processing status with a staged progress view (Extract → Chunk → Embed → Store) |
| **Embedding Generation** | Gemini `gemini-embedding-001` or fully offline Local TF-IDF fallback; stored in ChromaDB |
| **Semantic Search** | Top-k retrieval shown in an expandable panel before/with every answer |
| **Conversational Chat** | Natural chat UI, conversation history, and follow-up questions |
| **Source Citation** | Every answer includes document name, page number (if available), and chunk index |
| **Conversation Memory** | Session-scoped chat history used as context for follow-up questions |
| **Document Management** | View, delete, and refresh (re-embed) documents from the sidebar |
| **Professional UI** | Upload panel, chat window, document library, processing status, and statistics on one dashboard |
| **Hybrid Search (Bonus)** | Semantic + BM25 keyword fusion with adjustable weight |
| **Metadata Filtering (Bonus)** | Restrict search/chat to selected documents only |
| **Document Comparison (Bonus)** | Side-by-side LLM comparison of any two uploaded documents |
| **Auto Summarization (Bonus)** | On-demand per-document summary after processing |
| **Suggested Questions (Bonus)** | Auto-generated starter questions for each document |
| **Chat Export (Bonus)** | Export conversation as Markdown or JSON |
| **Token Usage Dashboard (Bonus)** | Running token count and estimated USD cost in the sidebar |
| **Dark Mode (Bonus)** | Toggle Dark Mode from the sidebar |
| **Answer Confidence Score (Bonus)** | Color-coded High / Medium / Low confidence badge based on retrieval similarity |
| **File Validation (Bonus)** | Rejects unsupported types, empty files, and files larger than 15 MB before processing |
| **Auto Chunk-size Suggestion (Bonus)** | Suggests a chunk size based on uploaded file size with a one-click **Use it** button |

## Setup

```bash
# 1. Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Gemini API key (backend only — it is never entered or shown in the app UI)
cp .env.example .env
# then edit .env and paste your key — get one at https://aistudio.google.com/apikey

# 4. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## API key handling

The Gemini API key lives **only** in the backend `.env` file (loaded automatically
via `python-dotenv`) or an environment variable — it is never typed into or
displayed by the app's UI. The sidebar only shows a green/yellow status
("key loaded" / "no key found"), so the key never appears on screen or in a
screenshot. To change the key, edit `.env` and restart the app.

## Accounts

Registered accounts are saved to `data/users.json` (username + salted hash of
the password) so you don't need to re-create an account every time you
restart the app. This file is a simple local JSON store meant for demos —
it is not encrypted at rest and should not be used to store real user
credentials in production. "Continue as guest" always works without an
account and doesn't touch this file.

## Running without an API key

The platform is fully usable without any API key: in the sidebar, set the
provider to **"Local TF-IDF (offline demo)"**. Embeddings are computed
locally with scikit-learn TF-IDF and answers are produced by an offline
extractive fallback that still retrieves and cites the correct passages —
useful for demos, grading, or environments without internet access. Switch
to **Gemini** at any time for true semantic embeddings and generated (rather
than extracted) answers, once a key is present in the backend `.env` file; use
"Refresh" on a document
in the sidebar to re-embed it under the new provider.

## Project structure

```
app.py                     Streamlit UI and orchestration
src/
  document_processor.py    Extraction (PDF/TXT/MD/DOCX), cleaning, chunking
  embeddings.py             Gemini + local TF-IDF embedding providers
  vector_store.py           ChromaDB wrapper: add/delete/refresh, semantic
                             + BM25 + hybrid search, metadata filtering
  llm.py                    Gemini chat wrapper (citations, summaries,
                             suggested questions, document comparison) +
                             offline fallback
  chat_session.py           Conversation memory + Markdown/JSON export
  utils.py                  Simulated auth helpers
data/chroma/                Persistent vector store (created on first run)
```

## Notes on design choices

- **Why ChromaDB?** Native metadata filtering (needed for "search specific
  documents only") and simple local persistence with no external server.
- **Why Gemini for embeddings/LLM?** Matches the stack already used
  elsewhere in this project; `gemini-embedding-001` and `gemini-2.5-flash`
  are used by default. Swapping in OpenAI/Anthropic would only require a
  new class in `embeddings.py` / `llm.py` implementing the same interface.
- **Page numbers:** PDFs track real page numbers per chunk. DOCX/TXT/MD have
  no fixed page concept, so citations show "page N/A" for those formats,
  consistent with the "page number if available" requirement.
- **Chunking:** paragraph/sentence-aware character-based splitter with
  configurable size and overlap (see Assignment 4 experiments for the
  reasoning behind good defaults — ~500 characters, 10–20% overlap).
