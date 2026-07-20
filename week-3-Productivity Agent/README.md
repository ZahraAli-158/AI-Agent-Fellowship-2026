# 1. Project Title

**Personal Productivity and Task Execution Agent**
*A tool-using AI agent for the AI-Agent-Fellowship-2026 (Track: AI Agents) — Week 3 Core Project*

Built by **Zahra** (2023-BS-AI-158-6B, BS Artificial Intelligence, The University of Faisalabad, Amin Campus) under supervisor **Dr.Gufran Rana**.

---

# 2. Problem Statement

Knowledge workers and students juggle tasks, meeting notes, and daily/weekly
planning across scattered tools, and re-typing the same information into a
to-do app, a notes app, and a planner wastes time. A general-purpose chatbot
doesn't solve this either — it can talk *about* your tasks, but can't
actually create, filter, complete, or schedule them safely.

This project builds an agent that **is not a chatbot**: it interprets a
request, decides whether a tool is needed, selects the right one, validates
its inputs, executes it against real persistent storage, asks for explicit
human approval before any write or irreversible action, and logs the entire
run — so it is both genuinely useful and safe to hand real data to.

---

# 3. Key Features

- **13 tools** (8 required + 5 bonus) covering task management, notes,
  meeting-notes extraction, planning, and reminders.
- **Human-approval gate**, enforced in *code* (not just prompted) before any
  write action — including a per-turn counter that force-gates creating
  multiple tasks in one request (a single, standalone task creation does
  not require approval).
- **Session memory** — follow-ups like "mark the second one complete"
  resolve correctly from the conversation just shown.
- **Full execution logging** — every run's tools, arguments, results,
  approval status, errors, and duration are recorded and reviewable in the
  Execution History tab.
- **Deterministic planning** — the work-plan/overdue/weekly-report tools use
  transparent, explainable scheduling logic, not another LLM call.
- **Sample data auto-seeded** on first run, so the app is demonstrable
  immediately.
- **44 automated tests**, all runnable offline (no live API key required).

---

# 4. Architecture Overview

```
User Interface (Streamlit, app/main.py)
        |
        v
Agent Graph (app/agent/graph.py)  <-- uses app/agent/nodes.py step functions
        |
        v
Intent & Tool Selection (Gemini function calling, app/agent/prompts.py)
        |
        v
Human Approval (if tool.requires_approval OR the code-level multi-task gate fires)
        |
        v
Tool Execution (app/tools/*)
        |
        v
Result Validation (Pydantic models, app/database/models.py)
        |
        v
Response Generation (Gemini, grounded in the tool's actual result)
        |
        v
Execution Log (SQLite, app/database/repository.py::LogRepository)
```

Full breakdown of every component, plus a rendered diagram, is in
[`docs/deliverables/Assignment3_Architecture_Diagram.docx`](docs/deliverables/Assignment3_Architecture_Diagram.docx)
and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

**Project structure:**

```
productivity-agent/
├── app/
│   ├── main.py, config.py
│   ├── agent/{graph.py, nodes.py, prompts.py, state.py}
│   ├── tools/{task_tools.py, note_tools.py, meeting_tools.py, planning_tools.py, bonus_tools.py, base.py, registry.py}
│   ├── database/{models.py, repository.py, seed.py}
│   ├── services/llm_service.py
│   └── logging/run_logger.py
├── tests/                 # 44 automated tests
├── docs/
│   ├── ARCHITECTURE.md, PROMPTS.md, LIMITS.md
│   └── deliverables/      # all assignment write-ups (docx/ipynb)
├── screenshots/
├── data/                  # SQLite file lives here (gitignored)
├── scripts/
│   └── check_api_key.py   # standalone Gemini key/connectivity sanity check
├── .env.example
├── requirements.txt
├── Dockerfile
└── README.md
```

---

# 5. Tool Catalogue

| # | Tool | Type | Approval Required |
|---|------|------|---|
| 1 | `create_task` | Write | No for 1st call/turn; **Yes** for 2nd+ (multi-task rule) |
| 2 | `list_tasks` | Read | No |
| 3 | `update_task` | Write | **Yes** |
| 4 | `complete_task` | Write | **Yes** |
| 5 | `search_notes` | Read | No |
| 6 | `save_note` | Write | No |
| 7 | `extract_meeting_actions` | Read (LLM sub-call) | No |
| 8 | `generate_work_plan` | Read | No |
| 9 | `create_reminder` | Write | **Yes** |
| 10 | `list_reminders` | Read | No |
| 11 | `draft_follow_up_email` | Read (LLM sub-call, drafts only) | **Yes** |
| 12 | `detect_overdue_tasks` | Read | No |
| 13 | `generate_weekly_report` | Read | No |

Full specification (input/output schema, errors, example call+result for
every tool) is in
[`docs/deliverables/Assignment4_Tool_Specification.docx`](docs/deliverables/Assignment4_Tool_Specification.docx)
— **note:** `list_reminders` was added after that document was written
(a small follow-up improvement so reminders are as chat-accessible as
they are in the UI's Reminders panel); see `app/tools/bonus_tools.py` for
its up-to-date specification.

---

# 6. Technology Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| LLM | Google Gemini API via the current `google-genai` SDK (function calling) |
| Data validation | Pydantic v2 |
| UI | Streamlit |
| Storage | SQLite (raw `sqlite3` + repository classes, no ORM) |
| Testing | pytest |
| Containerization | Docker |
| Secrets | Environment variables via `python-dotenv` |

---

# 7. Installation Steps

```bash
git clone <your-repo-url>
cd productivity-agent
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```
Then edit `.env` and set `GEMINI_API_KEY` (get one at https://aistudio.google.com/apikey).

---

# 8. Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GEMINI_API_KEY` | **Yes** | — | Your Gemini API key. Never committed — see `.env.example`. |
| `GEMINI_MODEL` | No | `gemini-3.1-flash-lite` | Model used for the agent loop and LLM sub-calls. |
| `DB_PATH` | No | `data/productivity_agent.db` | SQLite file location. |
| `MAX_AGENT_STEPS` | No | `8` | Requirement 9 execution limit. |
| `MAX_RETRIES_PER_TOOL` | No | `2` | Requirement 9 execution limit. |
| `TOOL_TIMEOUT_SECONDS` | No | `30` | Requirement 9 execution limit. |

Rationale for the default limits: [`docs/LIMITS.md`](docs/LIMITS.md).

---

# 9. How to Run Locally

```bash
# 1. Sanity-check your API key in isolation
python scripts/check_api_key.py

# 2. Run the app
streamlit run app/main.py
```
Opens at `http://localhost:8501`. Sample tasks/notes/a reminder are
auto-seeded on first run (see `app/database/seed.py`), so the Tasks and
Notes tabs are populated immediately.

**Docker alternative:**
```bash
docker build -t productivity-agent .
docker run -p 8501:8501 -e GEMINI_API_KEY=your_key_here productivity-agent
```

---

# 10. How to Run Tests

```bash
pytest tests/ -v
```
44 tests, all pass **without a live API key** — every test that would
otherwise need a real Gemini call stubs the response deterministically, so
the suite is fast, free, and safe to run in CI. Full requirement-to-test
mapping: [`docs/deliverables/Testing_Requirements_Report.docx`](docs/deliverables/Testing_Requirements_Report.docx).

---

# 11. Example User Requests

```
Explain the difference between High and Critical priority.
Create a task: buy groceries, high priority, due tomorrow.
Show me all high-priority tasks due this week.
Show me my high-priority tasks, then mark the second one as complete.
Create three tasks from these meeting notes: "We agreed to launch by Friday.
  Ali will prepare the deck. Sara will test the app."
Prepare a daily work plan, I have 5 hours today.
Find tasks that are overdue and recommend what I should work on first.
Draft a follow-up email based on these meeting notes.
Create a reminder for the project review on Friday.
Prepare a weekly productivity report.
Search my notes for the marketing campaign.
```

---

# 12. Evaluation Results

The full 32-case evaluation dataset (Direct Response, Single-Tool,
Multi-Tool, Approval, and Failure/Edge categories) and the metric
definitions/targets are in
[`docs/deliverables/Assignment5_Evaluation_Dataset.docx`](docs/deliverables/Assignment5_Evaluation_Dataset.docx).

> **Status: results pending live-API run.** The dataset and metric formulas
> are complete and ready to execute, but Actual Outcome / Pass-Fail and the
> 7 evaluation metrics require running every case against a real Gemini API
> key, which must be done by whoever holds that key. Run each case through
> the app (or automate it against `AgentController` directly), fill in the
> tables, then update this section with the final percentages, e.g.:
>
> | Metric | Target | Actual |
> |---|---|---|
> | Tool Selection Accuracy | ≥85% | *fill in* |
> | Argument Accuracy | ≥80% | *fill in* |
> | Task Completion Rate | ≥80% | *fill in* |
> | Approval Compliance | 100% | *fill in* |
> | Invalid Action Rate | <10% | *fill in* |

Experiment results (tool description quality, structured vs. unstructured
output, temperature, approval prompt design, max-steps, optional model
comparison) are similarly pending a live run — see
[`docs/deliverables/Assignment6_Experiments.ipynb`](docs/deliverables/Assignment6_Experiments.ipynb)
and its companion report.

---

# 13. Screenshots

> **Add your own screenshots here before submitting/publishing.** Suggested
> set (see `screenshots/README.md` for the full list): a direct-response
> answer, the approval card (Approve/Reject/Edit), the Tasks tab with
> seeded sample data, the Execution History tab, and one multi-tool
> workflow in progress.

```markdown
![Chat — direct response](screenshots/chat_direct_response.png)
![Approval card](screenshots/approval_card.png)
![Tasks tab](screenshots/tasks_tab.png)
![Execution history](screenshots/execution_history.png)
```

---

# 14. Demo Link

> **[ADD YOUR DEMO VIDEO LINK HERE]** — record a short walkthrough (chat →
> tool call → approval card → Tasks/Execution History tabs) and link it
> here (YouTube unlisted, Loom, or Google Drive).

---

# 15. Deployment Link

> **[ADD YOUR DEPLOYED APP URL HERE]** once deployed. Full step-by-step
> deployment instructions (Streamlit Community Cloud recommended, plus
> Railway/Render/Hugging Face alternatives via the included `Dockerfile`):
> [`docs/deliverables/Deployment_Guide.docx`](docs/deliverables/Deployment_Guide.docx).

---

# 16. Known Limitations

- **No authentication layer** — this is a single-local-user tool by design;
  the Execution History tab is visible to anyone with access to the running
  session. Documented as a trust-boundary assumption in the Security Review.
- **Ephemeral storage on some platforms** — Streamlit Community Cloud's
  filesystem does not guarantee the SQLite file survives a redeploy or a
  restart after inactivity. See the Deployment Guide for how to swap in a
  hosted Postgres/Supabase database if true persistence is required.
- **Session memory relies on conversation history, not an explicit code
  path** — references like "the second one" are resolved by Gemini reading
  the full conversation, not by a dedicated lookup function. Works in
  practice but is worth hardening if the conversation grows very long.
- **No rate limiting on the user side** — the app retries Gemini's own
  429/quota errors, but nothing stops rapid-fire local submissions from
  burning through API quota quickly.
- **Free-text fields have no maximum length** — an extremely large paste
  into `transcript`/`meeting_notes`/`content` could inflate token usage or
  approach the tool timeout.
- **No delete tool** — tasks can be cancelled (`status: Cancelled` via
  `update_task`) but not hard-deleted. This was a deliberate scope choice,
  not an oversight — see the Security Review's "Destructive Actions"
  section.
- **Live-API behavior not yet empirically measured** — the evaluation
  dataset and experiments are fully designed and offline-tested, but the
  actual percentages require a run against a live Gemini key (see
  "Evaluation Results" above).

---

# 17. Future Roadmap

- Run the full evaluation dataset and all 6 experiments against the live
  API and use the results to tune the system prompt and temperature.
- Add a dedicated, testable session-memory lookup (rather than relying
  solely on the model re-reading conversation history) for ordinal
  references like "the second one."
- Add per-user authentication if this ever moves beyond single-local-user
  use, and gate the Execution History tab accordingly.
- Migrate storage to Postgres/Supabase for true persistence across
  redeploys, with minimal changes needed outside `app/database/repository.py`.
- Add a local rate limit / minimum interval between submissions,
  independent of Gemini's own upstream quota handling.
- Add a max-length validator to free-text tool input fields.
- Consider a soft "Estimate Task Effort" and "Identify Conflicting
  Deadlines" bonus tool, using the same deterministic-scheduling approach
  as `generate_work_plan`.

---

## Additional Documentation

| Document | Location |
|---|---|
| Architecture Diagram | `docs/deliverables/Assignment3_Architecture_Diagram.docx` |
| Tool Specification | `docs/deliverables/Assignment4_Tool_Specification.docx` |
| Evaluation Dataset | `docs/deliverables/Assignment5_Evaluation_Dataset.docx` |
| Experiments (report + notebook) | `docs/deliverables/Assignment6_Experiments.docx` / `.ipynb` |
| Security Review | `docs/deliverables/Assignment7_Security_Review.docx` |
| Builder Journal | `docs/deliverables/Assignment8_Builder_Journal.docx` |
| Testing Requirements Report | `docs/deliverables/Testing_Requirements_Report.docx` |
| Deployment Guide | `docs/deliverables/Deployment_Guide.docx` |
| System Prompt (version-controlled) | `docs/PROMPTS.md` |
| Execution Limits Rationale | `docs/LIMITS.md` |
| Full Architecture Notes | `docs/ARCHITECTURE.md` |

## Code Quality & Testing Checklists

See the "Code Quality Requirements" and "Testing Requirements" sections
that were previously part of this README — now consolidated into
`docs/deliverables/Testing_Requirements_Report.docx` and this file's
sections 4-10 above, to avoid duplication.
