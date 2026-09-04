# Agents

Agents are a separate system from Workspaces. A Workspace assistant is a
configurable prompt (name, role, system prompt, temperature...) that
answers questions and can be grounded in your documents. An **Agent** goes
further: it has real Python tools it can call on its own, deciding turn by
turn whether to act (create a task, look something up, send an email)
before giving you its final answer. This is genuine Gemini function-calling
— the model itself picks which tool to use, not a hardcoded if/else.

## How it works

1. Each agent is defined in `app/agents/registry.py` — a key, name, icon,
   description, and a system prompt describing its job.
2. Its tools are built in `app/services/agent_service.py` as plain Python
   functions with docstrings and type hints (the docstring becomes the
   tool's description for the model; the type hints become its parameter
   schema).
3. `run_agent_turn()` passes those functions straight to
   `genai.GenerativeModel(tools=[...])` and starts a chat with
   `enable_automatic_function_calling=True` — the Gemini SDK handles the
   call/response loop: model decides to call a tool → SDK executes the
   Python function → result goes back to the model → model may call
   another tool or give a final text answer.
4. Every tool call made during a turn is logged (visible as 🔧 chips above
   the agent's reply in the chat UI) so you can see exactly what it did.

## The Meeting Agent

The first agent, focused entirely on turning meetings into tracked work.

**Tools:**
| Tool | What it does |
|---|---|
| `create_task(title, description, due_date)` | Creates a task |
| `list_tasks(status_filter)` | Lists tasks, optionally filtered by status |
| `update_task(task_id, ...)` | Updates a task's fields |
| `complete_task(task_id)` | Marks a task completed |
| `delete_task(task_id)` | Deletes a task |
| `extract_meeting_notes(raw_notes)` | Pulls structured decisions/action items out of pasted notes or a transcript |
| `send_email_summary(subject, body, to_email)` | Emails a summary to the user (or another address) |

Tasks can also be managed directly from the **Tasks** panel (add, check
off, delete) without going through chat at all — useful when Gemini isn't
configured, since tool-calling itself needs a real API key to reason about
when to act.

## Setting up email (optional)

The `send_email_summary` tool sends real email via Gmail SMTP. It needs:

```
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
```

`GMAIL_APP_PASSWORD` is **not** your normal Gmail password:
1. Turn on 2-Step Verification on the Google account.
2. Visit https://myaccount.google.com/apppasswords
3. Generate an app password for "Mail" and paste the 16-character value.

Without these set, the tool replies with a clear "email isn't configured"
message instead of failing silently or crashing the agent.

## Adding a new agent

1. Add an entry to `AGENTS` in `app/agents/registry.py` (key, name, icon,
   description, system_prompt).
2. Write a `build_<name>_tools(user_id, user_email, agent_key)` function in
   `app/services/agent_service.py` that returns a list of Python functions
   (closures bound to the current user).
3. Register it in `TOOL_BUILDERS` in the same file.

No route or template changes are needed — `/agents/<key>` and its chat/task
UI work for any registered agent automatically.
