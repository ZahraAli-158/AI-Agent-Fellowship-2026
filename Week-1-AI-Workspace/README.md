# 🧠 AI Workspace

A unified, professional interface for interacting with an AI language model — built as Assignment 3 of the AI-Agent-Fellowship-2026 program (Track: AI Agents).

Chat naturally, define a custom system prompt, switch models, use ready-made prompt templates, and keep your conversation history — all in one clean workspace. Two versions are included: a standalone HTML/JavaScript app and a Streamlit (Python) app.

---

## ✨ Features

### Required
- **Chat Interface** — natural, multi-turn conversation with the AI.
- **System Prompt** — pick a preset (Software Engineer, Research Assistant, Writing Coach) or write your own custom system prompt.
- **Model Selection** — switch between `gemini-2.5-flash` (balanced) and `gemini-2.5-flash-lite` (fastest), both on Google's free tier.
- **Prompt Templates** — one-click templates: Summarize Text, Explain Code, Generate Ideas, Rewrite Content, Translate, Create Email, Brainstorm. Each template opens its own separate conversation thread, so answers from different templates never mix together.
- **Conversation History** — full message history kept for each chat session.
- **Markdown Rendering** — responses render with proper formatting (bold, lists, code blocks, tables).
- **Error Handling** — clear handling of empty prompts, missing/invalid API keys, rate limits, and connection failures.
- **Responsive, Professional UI** — clean layout that works on desktop and mobile.

### Bonus
- Dark / Light Mode
- Export Chat — download the current conversation as a Markdown file.
- Save Custom Prompt Templates
- Token Usage Counter — estimated running total for the session.
- Response Time Measurement — shown under every AI response.
- Multiple Chat Sessions — create, switch between, and delete separate chats.
- Local Persistence (Streamlit version) — chat history and API key are saved to a local file so they survive closing and reopening the app.
- Per-Template Threads — switching templates (or the "General" tab) switches to a separate conversation thread within the same chat session, keeping each template's answers isolated from the others.

---

## 🏗️ Architecture

```
User Input (Chat / Template)
        |
   Frontend (HTML/JS  --or--  Streamlit UI)
        |
  Request builder
   - assembles full message history
   - attaches system prompt (as system_instruction)
   - selects chosen model
        |
  Google Gemini API
  POST generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
  header: x-goog-api-key
        |
  Response parsed (candidates[0].content.parts)
        |
  Rendered as Markdown -> appended to session history
```

**Request flow:** the user types a message or picks a template, then clicks Send. The app validates that the prompt isn't empty and that an API key is set, builds the full conversation (system prompt plus prior messages), and sends it directly to Gemini's `generateContent` endpoint using the user's own API key.

**Why Gemini:** Google AI Studio issues a free API key with no credit card required, making it easy to test and demo without any billing setup.

**Response flow:** the reply text is extracted from the response, rendered as Markdown, and the response time (ms) and an estimated token count are shown underneath it.

**Error handling:** every API call is wrapped in error handling that catches:
- an empty prompt (blocked before any request is sent)
- a missing or invalid API key (400 / 401 / 403)
- rate limiting (429)
- server errors (5xx)
- network/connection failures (request never reaches Google's servers)

Each case shows a clear, specific message instead of letting the app crash.

---

## 📦 Installation Guide

### Option A — HTML/JS version
No installation needed. Open `ai-workspace.html` directly in any modern browser, click "API key", and paste your Gemini key.

### Option B — Streamlit version

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Get a free Gemini API key**
1. Go to aistudio.google.com
2. Sign in with any Google account (no credit card required)
3. Click "Get API key" then "Create API key"
4. Copy the key (starts with `AIza...`)

**3. Set up your API key**

Copy `.env.example` to `.env` and add your real key:
```bash
cp .env.example .env
```
Then edit `.env`:
```
GEMINI_API_KEY=AIza-your-real-key-here
```
You can also skip this and paste your key directly into the sidebar at runtime — either way works.

**4. Run the app**
```bash
streamlit run ai_workspace_streamlit.py
```
The app opens automatically at `http://localhost:8501`. If you didn't set up a `.env` file, paste your API key in the sidebar — it's saved locally so you only need to enter it once.

---

## 🗂️ Project Structure

```
AI-Workspace/
├── ai-workspace.html          # Standalone HTML/JS version
├── ai_workspace_streamlit.py  # Streamlit (Python) version
├── requirements.txt           # Python dependencies for the Streamlit version
├── .env.example               # Template for setting GEMINI_API_KEY locally
├── ai_workspace_data.json     # Local history + API key (auto-created, git-ignored)
├── .gitignore
└── README.md                  # This file
```

---

## 🧪 How to Test Error Handling

- **Empty prompt** — click Send with nothing typed; a warning is shown and no API call is made.
- **Missing/invalid API key** — leave the key blank or enter a fake one; a clear invalid-key message is shown.
- **Connection failure** — disconnect your internet and send a message; a connection error message is shown.

## 🔀 How to Test Per-Template Threads

- Click **Summarize Text**, send a message, then click **Explain Code** — the chat area clears into a new, separate thread.
- Switch back using the thread tabs below the templates row — each template's history stays exactly where you left it, with no mixing between them.

---

## 👩‍💻 Author

Zahra Ali
BS Artificial Intelligence — The University of Faisalabad
AI-Agent-Fellowship-2026 — Track: AI Agents
