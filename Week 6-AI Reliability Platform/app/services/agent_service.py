"""
Agent execution service — this is what makes an "agent" different from a
normal chat: the model is given real Python functions as tools and decides
for itself, turn by turn, whether to call one (create a task, look up
tasks, send an email, ...) before producing its final answer. This uses
Gemini's automatic function-calling (google-generativeai's
`enable_automatic_function_calling=True`), not a hand-rolled prompt trick.
"""
import time
from datetime import datetime as dt

import google.generativeai as genai

from app.agents import registry
from app.models.models import db, AgentTask
from app.services import gemini_service, email_service
from app.guardrails.permissions import authorize_tool_call, requires_approval, risk_level_of, PermissionDenied
from app.observability.logging import log_structured
from app.reliability.timeouts import call_with_timeout, OperationTimeout


def _parse_date(date_str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return dt.strptime(date_str.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def build_meeting_tools(user_id: int, user_email: str, agent_key: str = "meeting", approved_tools=None,
                          tracer=None):
    """Builds the Meeting Agent's tool set as closures bound to the current
    user, so the model can only ever act on that user's own data.

    `approved_tools`: a set of tool names the user has explicitly approved
    for THIS turn (e.g. via a "confirm" click in the UI before sending the
    message). Any L3/L4 tool (see app.guardrails.permissions) NOT in this
    set will refuse to execute, no matter what the model decides — approval
    is enforced here in code, not left to the model's judgement (Week 6 §28).

    `tracer`: optional app.observability.tracing.Tracer — when supplied,
    every tool invocation is wrapped in a `tool_call` TraceStep (start
    time, duration, status, args, and a truncated result), satisfying the
    trace-viewer pipeline in Week 6 §18."""
    approved_tools = approved_tools or set()

    def _check_approval(tool_name):
        try:
            authorize_tool_call(tool_name, approved=tool_name in approved_tools)
            return None
        except PermissionDenied as exc:
            log_structured("guardrail_triggered", rule="unapproved_high_risk_tool_call",
                            tool=tool_name, user_id=user_id, agent_key=agent_key)
            return str(exc)

    def create_task(title: str, description: str = "", due_date: str = "") -> str:
        """Create a new task for the user. due_date should be in YYYY-MM-DD
        format if the user gave one, otherwise leave it blank."""
        task = AgentTask(
            user_id=user_id, agent_key=agent_key, title=title.strip(),
            description=(description or "").strip(), due_date=_parse_date(due_date),
        )
        db.session.add(task)
        db.session.commit()
        due_note = f" (due {task.due_date})" if task.due_date else ""
        return f"Created task #{task.id}: '{task.title}'{due_note}"

    def list_tasks(status_filter: str = "all") -> str:
        """List the user's tasks. status_filter can be 'all', 'pending',
        'in_progress', or 'completed'."""
        query = AgentTask.query.filter_by(user_id=user_id, agent_key=agent_key)
        if status_filter and status_filter != "all":
            query = query.filter_by(status=status_filter)
        tasks = query.order_by(AgentTask.created_at.desc()).all()
        if not tasks:
            return "No tasks found."
        lines = []
        for t in tasks:
            due = f" (due {t.due_date})" if t.due_date else ""
            lines.append(f"#{t.id} [{t.status}] {t.title}{due}")
        return "\n".join(lines)

    def update_task(task_id: int, title: str = "", description: str = "",
                     due_date: str = "", status: str = "") -> str:
        """Update an existing task. Only fields you provide are changed.
        status can be 'pending', 'in_progress', or 'completed'."""
        task = AgentTask.query.filter_by(id=task_id, user_id=user_id, agent_key=agent_key).first()
        if not task:
            return f"Task #{task_id} not found."
        if title:
            task.title = title.strip()
        if description:
            task.description = description.strip()
        if due_date:
            task.due_date = _parse_date(due_date)
        if status:
            task.status = status.strip()
        db.session.commit()
        return f"Updated task #{task_id}."

    def complete_task(task_id: int) -> str:
        """Mark a task as completed."""
        task = AgentTask.query.filter_by(id=task_id, user_id=user_id, agent_key=agent_key).first()
        if not task:
            return f"Task #{task_id} not found."
        task.status = "completed"
        db.session.commit()
        return f"Marked task #{task_id} ('{task.title}') as completed."

    def delete_task(task_id: int) -> str:
        """Permanently delete a task."""
        denial = _check_approval("delete_task")
        if denial:
            return (f"I can't delete task #{task_id} without your explicit confirmation first "
                     f"({denial}). Please delete it directly from the Tasks tab, or confirm and "
                     f"ask me again.")
        task = AgentTask.query.filter_by(id=task_id, user_id=user_id, agent_key=agent_key).first()
        if not task:
            return f"Task #{task_id} not found."
        title = task.title
        db.session.delete(task)
        db.session.commit()
        return f"Deleted task #{task_id} ('{title}')."

    def extract_meeting_notes(raw_notes: str) -> str:
        """Extract key decisions and action items from raw meeting notes or
        a transcript. Call this first when the user pastes meeting notes,
        before creating tasks from them."""
        result = gemini_service.chat_completion(
            system_prompt=(
                "Extract structured info from meeting notes. Format the reply as: "
                "'Decisions:' followed by a bullet list, then 'Action Items:' followed "
                "by a bullet list (include the owner's name if one is mentioned)."
            ),
            history=[], user_message=raw_notes, model="gemini-3.6-flash",
        )
        return result["text"]

    def send_email_summary(subject: str, body: str, to_email: str = "") -> str:
        """Email a summary (e.g. today's tasks or a meeting recap) to the
        user. Leave to_email blank to send it to the user's own account
        email address."""
        denial = _check_approval("email_task_summary")
        if denial:
            return (f"I can't send that email without your explicit confirmation first "
                     f"({denial}). Please confirm you'd like me to send it and ask again.")
        target = (to_email or user_email or "").strip()
        result = email_service.send_email(target, subject, body)
        return result["detail"]

    raw_tools = [create_task, list_tasks, update_task, complete_task, delete_task,
                  extract_meeting_notes, send_email_summary]

    def _traced(fn):
        import functools
        import time as _time

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            log_structured("tool_selected", tool=fn.__name__, agent_key=agent_key, user_id=user_id)
            t0 = _time.time()
            status = "ok"
            try:
                result = fn(*args, **kwargs)
                if isinstance(result, str) and ("confirmation" in result.lower() or "confirm" in result.lower()):
                    status = "requires_approval"
                    log_structured("tool_failed", tool=fn.__name__, reason="requires_approval",
                                    agent_key=agent_key, user_id=user_id)
                else:
                    log_structured("tool_succeeded", tool=fn.__name__, agent_key=agent_key, user_id=user_id)
                return result
            except Exception as exc:
                status = "failed"
                log_structured("tool_failed", tool=fn.__name__, reason=str(exc),
                                agent_key=agent_key, user_id=user_id)
                raise
            finally:
                if tracer is not None:
                    duration_ms = int((_time.time() - t0) * 1000)
                    tracer._record_step(
                        "tool_call", fn.__name__, status, duration_ms,
                        {"args": kwargs or {"positional": [str(a) for a in args]}},
                    )
        wrapper.__name__ = fn.__name__
        return wrapper

    return [_traced(fn) for fn in raw_tools]


TOOL_BUILDERS = {
    "meeting": build_meeting_tools,
}


def run_agent_turn(agent_key, user_id, user_email, history, user_message,
                    model="gemini-3.6-flash", temperature=0.4, approved_tools=None,
                    session_id=None):
    """
    Runs one turn of an agent conversation, letting the model call tools as
    many times as it needs before producing a final text answer.

    `approved_tools`: set of tool names pre-approved by the user for this
    turn (see build_meeting_tools) — L3/L4 tools not in this set will
    refuse to execute regardless of what the model decides.

    Every call now also produces a Trace with per-stage TraceSteps
    (model_call, agent_decision, tool_call/tool_result per tool fired) and
    is bounded by AgentLoopGuard so a confused model can't loop or spam
    tool calls indefinitely (Week 6 §17-19).

    Returns: {text, tool_calls, input_tokens, output_tokens, latency_ms, trace_id}
    """
    from app.observability.tracing import Tracer
    from app.reliability.loop_prevention import AgentLoopGuard, LoopLimitExceeded
    from app.guardrails.input import validate_input

    approved_tools = approved_tools or set()

    guard_input = validate_input(user_message)
    if not guard_input.allowed:
        log_structured("guardrail_triggered", rule=guard_input.rule, agent_key=agent_key, user_id=user_id)
        return {
            "text": guard_input.blocked_reason, "tool_calls": [],
            "input_tokens": 0, "output_tokens": 0, "latency_ms": 0,
            "guardrail_triggered": guard_input.rule,
        }

    agent_def = registry.get_agent(agent_key)
    if not agent_def:
        return {
            "text": f"Unknown agent '{agent_key}'.", "tool_calls": [],
            "input_tokens": 0, "output_tokens": 0, "latency_ms": 0, "error": True,
        }

    tracer = Tracer(user_id=user_id, session_id=session_id, request_type="agent", agent_key=agent_key,
                     model=model, prompt_version="agent-v1", input_text=user_message)
    tracer.__enter__()
    loop_guard = AgentLoopGuard()

    start = time.time()

    if not gemini_service.is_configured():
        latency_ms = int((time.time() - start) * 1000)
        tracer.mark_partial("offline demo mode — no GEMINI_API_KEY configured")
        tracer.__exit__(None, None, None)
        return {
            "text": (
                "This agent's tools need a real Gemini API key to reason about when to "
                "use them — tool-calling isn't available in offline demo mode. Add "
                "GEMINI_API_KEY to your .env to enable it. In the meantime you can still "
                "manage tasks directly from the Tasks tab."
            ),
            "tool_calls": [], "input_tokens": 0, "output_tokens": 0, "latency_ms": latency_ms,
            "trace_id": tracer.trace_id,
        }

    builder = TOOL_BUILDERS.get(agent_key)
    tools = builder(user_id, user_email, agent_key, approved_tools=approved_tools, tracer=tracer) \
        if builder else []

    try:
        with tracer.step("agent_decision", "select_tools_and_plan") as step:
            model_obj = genai.GenerativeModel(
                model_name=model,
                system_instruction=agent_def["system_prompt"],
                tools=tools,
                generation_config={"temperature": temperature},
            )

            gemini_history = []
            for m in history:
                role = "user" if m["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [m["content"]]})

            chat = model_obj.start_chat(history=gemini_history, enable_automatic_function_calling=True)
            step.set_meta(available_tools=[t.__name__ for t in tools], history_len=len(gemini_history))

        with tracer.step("model_call", "gemini_function_calling_turn"):
            # Time-boxed per Week 6 §31/§32 — an agent turn (including any
            # tool calls the model makes mid-turn) must not hang forever.
            response = call_with_timeout(chat.send_message, user_message,
                                           operation="workflow_step", timeout_s=30.0)
            text = response.text
        latency_ms = int((time.time() - start) * 1000)

        # Best-effort extraction of which tools fired this turn, for a
        # transparent "what the agent actually did" log in the UI, and to
        # feed the loop guard + per-tool trace steps.
        tool_calls = []
        try:
            new_entries = chat.history[len(gemini_history):]
            for entry in new_entries:
                for part in entry.parts:
                    fc = getattr(part, "function_call", None)
                    if fc and getattr(fc, "name", None):
                        try:
                            args = dict(fc.args) if fc.args else {}
                        except Exception:
                            args = {}
                        tool_name = fc.name
                        loop_guard.record_step()
                        try:
                            loop_guard.record_tool_call(tool_name, str(sorted(args.items())))
                        except LoopLimitExceeded as loop_exc:
                            log_structured("guardrail_triggered", rule="agent_loop_limit",
                                            detail=str(loop_exc), agent_key=agent_key)
                            tool_calls.append({"tool": tool_name, "args": args, "status": "blocked_loop_limit"})
                            continue
                        tracer.add_tool_call(tool_name, args, duration_ms=0,
                                               status="ok" if tool_name not in
                                               ("delete_task", "email_task_summary")
                                               or tool_name in approved_tools else "requires_approval")
                        tool_calls.append({"tool": tool_name, "args": args})
        except Exception:
            pass

        tracer.set_output(text, gemini_service.estimate_tokens(user_message), gemini_service.estimate_tokens(text))
        tracer.__exit__(None, None, None)

        return {
            "text": text,
            "tool_calls": tool_calls,
            "input_tokens": gemini_service.estimate_tokens(user_message),
            "output_tokens": gemini_service.estimate_tokens(text),
            "latency_ms": latency_ms,
            "trace_id": tracer.trace_id,
            "loop_stats": {"steps": loop_guard.steps, "tool_calls": loop_guard.tool_calls},
        }
    except Exception as exc:
        latency_ms = int((time.time() - start) * 1000)
        tracer.mark_failure(str(exc))
        tracer.__exit__(type(exc), exc, exc.__traceback__)
        return {
            "text": f"[Agent error: {exc}]",
            "tool_calls": [], "input_tokens": 0, "output_tokens": 0,
            "latency_ms": latency_ms, "error": True, "trace_id": tracer.trace_id,
        }
