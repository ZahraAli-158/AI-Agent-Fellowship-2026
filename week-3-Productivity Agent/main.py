"""Streamlit UI — Requirement 1.

Panels: chat input + conversation display, agent status, tool execution
status, approval requests, task/notes panel, execution history, and clear
error messages. No chain-of-thought is ever displayed — only short
operational status strings.

NOTE: This file is presentation-only. Every call into the agent
(AgentController.start_turn / approve_pending), every repository read
(TaskRepository / NoteRepository / ReminderRepository / LogRepository),
and every data model is used exactly as before — only layout, styling and
information architecture changed.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.graph import AgentController, TurnResult
from app.config import MissingAPIKeyError, settings
from app.database.models import Status
from app.database.repository import init_db
from app.database.repository import LogRepository
from app.database.repository import NoteRepository
from app.database.repository import ReminderRepository
from app.database.repository import TaskRepository
from app.database.seed import seed_sample_data
from app.logging.run_logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="Productivity Agent",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================================
# THEME — Black + Crimson premium SaaS dashboard
# =====================================================================
_THEME_CSS = """
<style>
:root{
    --bg:#0F0F10;
    --card:#1A1A1D;
    --sidebar:#111113;
    --primary:#E11D48;
    --accent:#DC2626;
    --hover:#F43F5E;
    --border:#2A2A2F;
    --text:#FFFFFF;
    --text-secondary:#A1A1AA;
    --success:#22C55E;
    --warning:#F59E0B;
    --error:#EF4444;
    --info:#3B82F6;
}

html, body, [class*="css"], .stApp{
    font-family:-apple-system, 'Segoe UI', Inter, Roboto, sans-serif !important;
    background-color:var(--bg) !important;
    color:var(--text) !important;
}

.stApp{ background:radial-gradient(1200px 600px at 90% -10%, rgba(225,29,72,0.08), transparent 60%), var(--bg) !important; }

#MainMenu, footer, header{visibility:hidden;}

section[data-testid="stSidebar"]{
    background-color:var(--sidebar) !important;
    border-right:1px solid var(--border);
}
section[data-testid="stSidebar"] .block-container{padding-top:1.2rem;}

h1,h2,h3,h4,h5,h6{ color:var(--text) !important; letter-spacing:-0.01em; }
p, span, label, .stCaption, div{ color:var(--text); }
small, .stCaption, [data-testid="stCaptionContainer"]{ color:var(--text-secondary) !important; }

/* ---------- Buttons ---------- */
.stButton>button, .stFormSubmitButton>button{
    background:linear-gradient(135deg, var(--primary), var(--accent)) !important;
    color:#fff !important;
    border:none !important;
    border-radius:12px !important;
    padding:0.55rem 1.1rem !important;
    font-weight:600 !important;
    transition:all .18s ease-in-out !important;
    box-shadow:0 2px 10px rgba(225,29,72,0.25);
}
.stButton>button:hover, .stFormSubmitButton>button:hover{
    background:linear-gradient(135deg, var(--hover), var(--primary)) !important;
    box-shadow:0 6px 18px rgba(225,29,72,0.4);
    transform:translateY(-1px);
}
.stButton>button:active{ transform:translateY(0px); }

/* Secondary / reject-style buttons: second form submit button in a row */
div[data-testid="column"]:nth-of-type(2) .stFormSubmitButton>button{
    background:#242427 !important;
    border:1px solid var(--border) !important;
    box-shadow:none;
}
div[data-testid="column"]:nth-of-type(2) .stFormSubmitButton>button:hover{
    background:var(--error) !important;
}

/* ---------- Inputs ---------- */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"]>div,
.stMultiSelect div[data-baseweb="select"]>div, .stDateInput input{
    background-color:#151518 !important;
    color:var(--text) !important;
    border:1px solid var(--border) !important;
    border-radius:10px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus{
    border-color:var(--primary) !important;
    box-shadow:0 0 0 2px rgba(225,29,72,0.25) !important;
}

/* ---------- Tabs (top nav) ---------- */
.stTabs [data-baseweb="tab-list"]{
    gap:6px;
    border-bottom:1px solid var(--border);
}
.stTabs [data-baseweb="tab"]{
    background-color:transparent;
    color:var(--text-secondary) !important;
    border-radius:10px 10px 0 0;
    padding:10px 18px;
    font-weight:600;
}
.stTabs [aria-selected="true"]{
    color:var(--text) !important;
    background:linear-gradient(180deg, rgba(225,29,72,0.15), rgba(225,29,72,0.03));
    border-bottom:2px solid var(--primary) !important;
}

/* ---------- Generic card ---------- */
.pa-card{
    background:var(--card);
    border:1px solid var(--border);
    border-radius:16px;
    padding:18px 20px;
    margin-bottom:14px;
    box-shadow:0 1px 2px rgba(0,0,0,0.4);
    transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease;
}
.pa-card:hover{
    transform:translateY(-2px);
    border-color:#3a3a40;
    box-shadow:0 10px 24px rgba(0,0,0,0.45);
}

/* ---------- Header ---------- */
.pa-header{
    display:flex; align-items:center; justify-content:space-between;
    background:var(--card);
    border:1px solid var(--border);
    border-radius:16px;
    padding:18px 26px;
    margin-bottom:20px;
    box-shadow:0 1px 2px rgba(0,0,0,0.4);
}
.pa-header-left{ display:flex; align-items:center; gap:14px; }
.pa-logo{
    width:46px;height:46px;border-radius:13px;
    background:linear-gradient(135deg, var(--primary), var(--accent));
    display:flex;align-items:center;justify-content:center;
    font-size:22px; box-shadow:0 4px 14px rgba(225,29,72,0.4);
}
.pa-title{ font-size:1.35rem; font-weight:800; margin:0; line-height:1.1; }
.pa-subtitle{ font-size:0.85rem; color:var(--text-secondary); margin:2px 0 0 0; }
.pa-header-right{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; justify-content:flex-end;}

/* ---------- Badges ---------- */
.pa-badge{
    display:inline-flex; align-items:center; gap:6px;
    padding:4px 12px; border-radius:999px;
    font-size:0.76rem; font-weight:700; letter-spacing:.01em;
    border:1px solid transparent; white-space:nowrap;
}
.b-idle{ background:rgba(34,197,94,0.12); color:var(--success); border-color:rgba(34,197,94,0.35); }
.b-thinking{ background:rgba(59,130,246,0.12); color:var(--info); border-color:rgba(59,130,246,0.35); }
.b-tool{ background:rgba(225,29,72,0.12); color:var(--hover); border-color:rgba(225,29,72,0.35); }
.b-waiting{ background:rgba(245,158,11,0.14); color:var(--warning); border-color:rgba(245,158,11,0.4); }
.b-executing{ background:rgba(225,29,72,0.16); color:var(--primary); border-color:rgba(225,29,72,0.4); }
.b-error{ background:rgba(239,68,68,0.14); color:var(--error); border-color:rgba(239,68,68,0.4); }
.b-completed{ background:rgba(34,197,94,0.12); color:var(--success); border-color:rgba(34,197,94,0.35); }
.b-neutral{ background:#232327; color:var(--text-secondary); border-color:var(--border); }
.b-model{ background:rgba(59,130,246,0.10); color:var(--info); border-color:rgba(59,130,246,0.3);}
.b-session{ background:rgba(34,197,94,0.10); color:var(--success); border-color:rgba(34,197,94,0.3);}

/* Priority badges */
.pr-critical{ background:rgba(239,68,68,0.15); color:#F87171; border:1px solid rgba(239,68,68,0.4);}
.pr-high{ background:rgba(249,115,22,0.15); color:#FB923C; border:1px solid rgba(249,115,22,0.4);}
.pr-medium{ background:rgba(245,158,11,0.15); color:#FBBF24; border:1px solid rgba(245,158,11,0.4);}
.pr-low{ background:rgba(59,130,246,0.15); color:#60A5FA; border:1px solid rgba(59,130,246,0.4);}

/* Status badges (tasks) */
.st-completed{ background:rgba(34,197,94,0.15); color:#4ADE80; border:1px solid rgba(34,197,94,0.4);}
.st-blocked{ background:rgba(168,85,247,0.15); color:#C084FC; border:1px solid rgba(168,85,247,0.4);}
.st-pending{ background:rgba(161,161,170,0.15); color:#D4D4D8; border:1px solid rgba(161,161,170,0.35);}
.st-progress{ background:rgba(59,130,246,0.15); color:#60A5FA; border:1px solid rgba(59,130,246,0.4);}
.st-cancelled{ background:rgba(239,68,68,0.1); color:#F87171; border:1px solid rgba(239,68,68,0.3);}

/* ---------- Stat tiles ---------- */
.pa-stat{
    background:var(--card); border:1px solid var(--border); border-radius:14px;
    padding:12px 14px; text-align:left; transition:transform .15s ease;
}
.pa-stat:hover{ transform:translateY(-2px); border-color:#3a3a40; }
.pa-stat .num{ font-size:1.5rem; font-weight:800; line-height:1.1; }
.pa-stat .lbl{ font-size:0.72rem; color:var(--text-secondary); text-transform:uppercase; letter-spacing:.04em;}

/* ---------- Chat bubbles ---------- */
div[data-testid="stChatMessage"]{
    background:transparent !important;
    border:none !important;
    padding:2px 0 !important;
}
.pa-msg-user{
    background:#202024; border:1px solid var(--border); border-radius:14px;
    padding:12px 16px; color:var(--text); margin-left:auto; max-width:100%;
}
.pa-msg-assistant{
    background:var(--card); border-left:3px solid var(--primary); border-radius:12px;
    padding:12px 16px; color:var(--text);
}

/* Divider */
hr, .stDivider{ border-color:var(--border) !important; }

/* Expander */
details, .streamlit-expanderHeader{
    background:var(--card) !important; border:1px solid var(--border) !important;
    border-radius:12px !important;
}
summary{ color:var(--text) !important; font-weight:600; }

/* Sidebar section title */
.pa-side-title{
    font-size:0.72rem; text-transform:uppercase; letter-spacing:.06em;
    color:var(--text-secondary); margin:16px 0 8px 0; font-weight:700;
}
</style>
"""
st.markdown(_THEME_CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------- init --
init_db()
logger.info("Application started (model=%s, db_path=%s).", settings.gemini_model, settings.db_path)

if seed_sample_data():
    logger.info("Fresh database detected — sample tasks/notes/reminder seeded.")

if "controller" not in st.session_state:
    st.session_state.controller = AgentController()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_status" not in st.session_state:
    st.session_state.agent_status = "Idle"
if "pending" not in st.session_state:
    st.session_state.pending = None
if "last_error" not in st.session_state:
    st.session_state.last_error = None
if "queued_input" not in st.session_state:
    st.session_state.queued_input = None

controller: AgentController = st.session_state.controller
task_repo = TaskRepository()
note_repo = NoteRepository()
reminder_repo = ReminderRepository()
log_repo = LogRepository()


def set_status(s: str) -> None:
    st.session_state.agent_status = s


def handle_turn_result(result: TurnResult) -> None:
    st.session_state.last_error = None
    if result.status == "final":
        st.session_state.messages.append({"role": "assistant", "content": result.text})
        set_status("Idle")
        st.session_state.pending = None
    elif result.status == "pending_approval":
        st.session_state.pending = {
            "tool_name": result.tool_name,
            "arguments": result.arguments,
            "expected_effect": result.expected_effect,
        }
        set_status(f"Waiting for approval: {result.tool_name}")
    elif result.status == "error":
        st.session_state.last_error = result.text
        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {result.text}"})
        set_status("Error")
    else:
        set_status("Idle")


def submit_user_message(text: str) -> None:
    """Same path as the chat input box — used by both the chat box and the
    sidebar Quick Action buttons so backend behavior is identical."""
    st.session_state.messages.append({"role": "user", "content": text})
    live_trace: list[str] = []

    def live_status(s: str) -> None:
        set_status(s)
        live_trace.append(s)

    result = controller.start_turn(text, status_cb=live_status)
    handle_turn_result(result)


# =====================================================================
# STATUS BADGE HELPERS (presentation only)
# =====================================================================
def status_badge_class(status: str) -> str:
    s = status.lower()
    if s.startswith("idle"):
        return "b-idle"
    if s.startswith("thinking"):
        return "b-thinking"
    if s.startswith("selecting tool"):
        return "b-tool"
    if s.startswith("waiting"):
        return "b-waiting"
    if s.startswith("executing"):
        return "b-executing"
    if s.startswith("error") or "failed" in s:
        return "b-error"
    if s.startswith("reviewing"):
        return "b-tool"
    if "rejected" in s:
        return "b-neutral"
    return "b-neutral"


def status_icon(status: str) -> str:
    s = status.lower()
    if s.startswith("idle"):
        return "🟢"
    if s.startswith("thinking"):
        return "🧠"
    if s.startswith("selecting tool"):
        return "🛠"
    if s.startswith("waiting"):
        return "⏳"
    if s.startswith("executing"):
        return "⚡"
    if s.startswith("error") or "failed" in s:
        return "❌"
    if s.startswith("reviewing"):
        return "🔎"
    if "rejected" in s:
        return "🚫"
    return "⚙️"


def badge(text: str, css_class: str) -> str:
    return f'<span class="pa-badge {css_class}">{text}</span>'


def priority_badge(priority_value: str) -> str:
    cls = {
        "Critical": "pr-critical", "High": "pr-high",
        "Medium": "pr-medium", "Low": "pr-low",
    }.get(priority_value, "pr-medium")
    return badge(priority_value, cls)


def status_badge(status_value: str) -> str:
    cls = {
        "Completed": "st-completed", "Blocked": "st-blocked",
        "Pending": "st-pending", "In Progress": "st-progress",
        "Cancelled": "st-cancelled",
    }.get(status_value, "st-pending")
    return badge(status_value, cls)


def stat_tile(label: str, value: object) -> str:
    return f'<div class="pa-stat"><div class="num">{value}</div><div class="lbl">{label}</div></div>'


# =====================================================================
# HEADER
# =====================================================================
_today = date.today().isoformat()
_status = st.session_state.agent_status
st.markdown(
    f"""
    <div class="pa-header">
        <div class="pa-header-left">
            <div class="pa-logo">🤖</div>
            <div>
                <p class="pa-title">Personal Productivity Agent</p>
                <p class="pa-subtitle">AI-powered task management, planning, notes and reminders</p>
            </div>
        </div>
        <div class="pa-header-right">
            {badge("📅 " + _today, "b-neutral")}
            {badge("⚙️ " + settings.gemini_model, "b-model")}
            {badge(status_icon(_status) + " " + _status, status_badge_class(_status))}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not settings.gemini_api_key:
    st.error(
        "No Gemini API key configured. Copy `.env.example` to `.env` and set "
        "`GEMINI_API_KEY`, then restart the app.",
        icon="🚫",
    )
    st.stop()

# =====================================================================
# SIDEBAR
# =====================================================================
with st.sidebar:
    st.markdown('<p class="pa-side-title">Agent Status</p>', unsafe_allow_html=True)
    all_statuses = ["Idle", "Thinking…", "Selecting Tool", "Waiting Approval", "Executing", "Error"]
    current = st.session_state.agent_status
    st.markdown(badge(status_icon(current) + " " + current, status_badge_class(current)), unsafe_allow_html=True)
    if st.session_state.last_error:
        st.error(st.session_state.last_error, icon="⚠️")

    st.markdown('<p class="pa-side-title">Dashboard Statistics</p>', unsafe_allow_html=True)
    _all_tasks = task_repo.list()
    _all_notes = note_repo.list()
    _all_reminders = reminder_repo.list()
    _today_iso = date.today().isoformat()
    _total = len(_all_tasks)
    _pending_n = sum(1 for t in _all_tasks if t.status == Status.PENDING)
    _completed_n = sum(1 for t in _all_tasks if t.status == Status.COMPLETED)
    _blocked_n = sum(1 for t in _all_tasks if t.status == Status.BLOCKED)
    _overdue_n = sum(
        1 for t in _all_tasks
        if t.due_date and t.due_date < _today_iso and t.status not in (Status.COMPLETED, Status.CANCELLED)
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(stat_tile("Total Tasks", _total), unsafe_allow_html=True)
        st.markdown(stat_tile("Completed", _completed_n), unsafe_allow_html=True)
        st.markdown(stat_tile("Notes", len(_all_notes)), unsafe_allow_html=True)
    with c2:
        st.markdown(stat_tile("Pending", _pending_n), unsafe_allow_html=True)
        st.markdown(stat_tile("Blocked", _blocked_n), unsafe_allow_html=True)
        st.markdown(stat_tile("Reminders", len(_all_reminders)), unsafe_allow_html=True)
    st.markdown(stat_tile("Overdue", _overdue_n), unsafe_allow_html=True)

    st.markdown('<p class="pa-side-title">Quick Actions</p>', unsafe_allow_html=True)
    qa_disabled = bool(st.session_state.pending)
    if st.button("➕ New Task", use_container_width=True, disabled=qa_disabled, key="qa_task"):
        st.session_state.queued_input = "I'd like to create a new task. Please ask me for the details."
        st.rerun()
    if st.button("🔔 New Reminder", use_container_width=True, disabled=qa_disabled, key="qa_reminder"):
        st.session_state.queued_input = "I'd like to set a new reminder. Please ask me for the details."
        st.rerun()
    if st.button("📝 Save Note", use_container_width=True, disabled=qa_disabled, key="qa_note"):
        st.session_state.queued_input = "I'd like to save a new note. Please ask me for the details."
        st.rerun()
    if st.button("📊 Weekly Report", use_container_width=True, disabled=qa_disabled, key="qa_report"):
        st.session_state.queued_input = "Please generate my weekly report."
        st.rerun()

    st.markdown('<p class="pa-side-title">Session Memory</p>', unsafe_allow_html=True)
    _conv_chars = sum(len(m["content"]) for m in st.session_state.messages)
    st.markdown(
        f"""<div class="pa-card" style="padding:12px 14px;">
        <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-secondary);">Messages</span><b>{len(st.session_state.messages)}</b></div>
        <div style="display:flex;justify-content:space-between;margin-top:6px;"><span style="color:var(--text-secondary);">Current Session</span><b>Active</b></div>
        <div style="display:flex;justify-content:space-between;margin-top:6px;"><span style="color:var(--text-secondary);">Conversation Size</span><b>{_conv_chars} chars</b></div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Conversation", use_container_width=True, key="clear_conv"):
        st.session_state.controller = AgentController()
        st.session_state.messages = []
        st.session_state.pending = None
        st.session_state.agent_status = "Idle"
        st.session_state.queued_input = None
        st.rerun()

# =====================================================================
# MAIN TABS
# =====================================================================
tab_chat, tab_tasks, tab_reminders, tab_notes, tab_logs = st.tabs(
    ["💬 Chat", "📋 Tasks", "🔔 Reminders", "📝 Notes", "📜 Execution History"]
)

# ============================================================= CHAT TAB ==
with tab_chat:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            bubble_class = "pa-msg-user" if msg["role"] == "user" else "pa-msg-assistant"
            st.markdown(f'<div class="{bubble_class}">{msg["content"]}</div>', unsafe_allow_html=True)

    # ---------------------------------------------------------- approval --
    if st.session_state.pending:
        p = st.session_state.pending

        # ---- Fix for the "Edit Arguments" crash --------------------------
        # Streamlit forbids writing to `st.session_state[<widget_key>]` in
        # the *same* script run after a widget with that key has already
        # been instantiated (it raises StreamlitAPIException: "cannot be
        # modified after the widget ... is instantiated"). The old code
        # created the `edit_toggle` widget first and then, further down,
        # tried to flip `st.session_state["edit_toggle"] = True` in reaction
        # to the "Edit Arguments" button — which crashed the page every
        # time, so the toggle never actually switched to edit mode (hence
        # both "it errors" and "it doesn't let me edit").
        #
        # Fix: use a plain (non-widget) flag, `_force_edit_mode`, that gets
        # set + a rerun triggered when "Edit Arguments" is clicked. On the
        # *next* run, we consume that flag and pre-seed `edit_toggle`
        # BEFORE the toggle widget is created below — which Streamlit
        # allows, since the widget hasn't been instantiated yet this run.
        if st.session_state.pop("_force_edit_mode", False):
            st.session_state["edit_toggle"] = True

        with st.chat_message("assistant"):
            st.markdown(
                f"""<div class="pa-card" style="border-left:3px solid var(--warning);">
                {badge("⏳ Waiting Approval", "b-waiting")}
                <div style="margin-top:12px;"><span style="color:var(--text-secondary);">Tool Name</span><br>
                <b style="font-size:1.05rem;">{p['tool_name']}</b></div>
                <div style="margin-top:10px;"><span style="color:var(--text-secondary);">Expected Effect</span><br>
                {p['expected_effect']}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            st.markdown('<p style="color:var(--text-secondary);margin-bottom:4px;">Input Arguments</p>', unsafe_allow_html=True)

            edit_mode = st.toggle("✏️ Edit arguments before approving", key="edit_toggle")

            # IMPORTANT: the text_area and both buttons live inside a single
            # st.form(). Streamlit only sends a widget's latest value to the
            # backend when its *own* change event fires (e.g. on blur) — if a
            # user types a new value and clicks "Approve" quickly, the click
            # can reach the server before that commit does, so the OLD value
            # gets used (this was the "edited arguments not applied" bug).
            # A form bundles every widget inside it together with whichever
            # submit button was pressed, in one atomic message, which removes
            # that race entirely.
            with st.form(key="approval_form", clear_on_submit=False):
                if edit_mode:
                    edited_json = st.text_area(
                        "Arguments (JSON) — edit, then click Approve",
                        value=json.dumps(p["arguments"], indent=2, default=str),
                        key="edit_json",
                        height=140,
                    )
                else:
                    st.json(p["arguments"])
                    edited_json = None

                c1, c2, c3 = st.columns(3)
                approve_clicked = c1.form_submit_button(
                    "✅ Approve", use_container_width=True, key="approve_btn",
                    disabled=st.session_state.get("_approval_busy", False),
                )
                reject_clicked = c2.form_submit_button(
                    "❌ Reject", use_container_width=True, key="reject_btn",
                    disabled=st.session_state.get("_approval_busy", False),
                )
                edit_hint = c3.form_submit_button(
                    "✏️ Edit Arguments", use_container_width=True, key="edit_hint_btn",
                    disabled=edit_mode or st.session_state.get("_approval_busy", False),
                )

            if edit_hint and not edit_mode:
                st.session_state["_force_edit_mode"] = True
                st.rerun()

            # Guard against double-submits (e.g. an impatient extra click
            # while the previous approve/reject is still being processed)
            # calling controller.approve_pending() a second time after
            # `st.session_state.pending` has already been cleared/advanced
            # — which is what produced the repeated "There is no pending
            # approval to act on." messages.
            if (approve_clicked or reject_clicked) and not st.session_state.get("_approval_busy", False):
                st.session_state["_approval_busy"] = True

                if approve_clicked:
                    if edit_mode:
                        try:
                            edited_args = json.loads(edited_json)
                        except json.JSONDecodeError:
                            st.error("Invalid JSON — fix it above and click Approve again.")
                            edited_args = None
                    else:
                        edited_args = p["arguments"]

                    if edited_args is not None:
                        if edit_mode and edited_args != p["arguments"]:
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"✏️ Using your edited arguments instead of the original proposal: `{edited_args}`",
                            })
                        set_status(f"Executing '{p['tool_name']}'…")
                        result = controller.approve_pending(True, edited_arguments=edited_args, status_cb=set_status)
                        handle_turn_result(result)
                        st.session_state["_approval_busy"] = False
                        st.rerun()
                    else:
                        st.session_state["_approval_busy"] = False

                elif reject_clicked:
                    set_status("Rejecting action…")
                    result = controller.approve_pending(False, status_cb=set_status)
                    handle_turn_result(result)
                    st.session_state["_approval_busy"] = False
                    st.rerun()

    # ---------------------------------------------------------- chat input --
    user_input = st.chat_input(
        "Ask me to create tasks, plan your day, search notes, summarize meeting notes…",
        disabled=bool(st.session_state.pending),
    )

    if st.session_state.queued_input and not st.session_state.pending:
        user_input = st.session_state.queued_input
        st.session_state.queued_input = None

    if user_input:
        with st.chat_message("user"):
            st.markdown(f'<div class="pa-msg-user">{user_input}</div>', unsafe_allow_html=True)
        with st.chat_message("assistant"):
            status_placeholder = st.empty()

            def live_status(s: str) -> None:
                set_status(s)
                status_placeholder.markdown(
                    badge(status_icon(s) + " " + s, status_badge_class(s)), unsafe_allow_html=True
                )

            st.session_state.messages.append({"role": "user", "content": user_input})
            result = controller.start_turn(user_input, status_cb=live_status)
            status_placeholder.empty()
            handle_turn_result(result)
        st.rerun()

    st.divider()
    st.caption("Try: \"Create three tasks from these meeting notes: ...\" · "
               "\"Show me all high-priority tasks due this week\" · "
               "\"Prepare a daily work plan, I have 5 hours today\" · "
               "\"Find overdue tasks and tell me what to work on first\"")

# ============================================================ TASKS TAB ==
with tab_tasks:
    tasks_all = task_repo.list()

    total = len(tasks_all)
    pending_n = sum(1 for t in tasks_all if t.status == Status.PENDING)
    completed_n = sum(1 for t in tasks_all if t.status == Status.COMPLETED)
    blocked_n = sum(1 for t in tasks_all if t.status == Status.BLOCKED)
    overdue_n = sum(
        1 for t in tasks_all
        if t.due_date and t.due_date < _today_iso and t.status not in (Status.COMPLETED, Status.CANCELLED)
    )

    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    for col, (lbl, val) in zip(
        (sc1, sc2, sc3, sc4, sc5),
        [("Total", total), ("Pending", pending_n), ("Completed", completed_n),
         ("Blocked", blocked_n), ("Overdue", overdue_n)],
    ):
        with col:
            st.markdown(stat_tile(lbl, val), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    fc1, fc2, fc3, fc4, fc5 = st.columns([2, 1, 1, 1, 1])
    search_q = fc1.text_input("🔎 Search tasks", key="task_search", placeholder="Search by title or description…")
    priority_filter = fc2.selectbox("Priority", ["All", "Critical", "High", "Medium", "Low"], key="task_pf")
    status_filter = fc3.selectbox(
        "Status", ["All", "Pending", "In Progress", "Blocked", "Completed", "Cancelled"], key="task_sf"
    )
    all_tags = sorted({tag for t in tasks_all for tag in t.tags})
    tag_filter = fc4.selectbox("Tag", ["All"] + all_tags, key="task_tf")
    date_filter = fc5.text_input("Due before", key="task_df", placeholder="YYYY-MM-DD")

    filtered = tasks_all
    if search_q:
        ql = search_q.lower()
        filtered = [t for t in filtered if ql in t.title.lower() or ql in t.description.lower()]
    if priority_filter != "All":
        filtered = [t for t in filtered if t.priority.value == priority_filter]
    if status_filter != "All":
        filtered = [t for t in filtered if t.status.value == status_filter]
    if tag_filter != "All":
        filtered = [t for t in filtered if tag_filter in t.tags]
    if date_filter:
        filtered = [t for t in filtered if t.due_date and t.due_date <= date_filter]

    st.markdown("<br>", unsafe_allow_html=True)

    if not filtered:
        st.caption("No tasks match — ask the agent to create some in the Chat tab.")
    else:
        for t in filtered:
            is_overdue = (
                t.due_date and t.due_date < _today_iso
                and t.status not in (Status.COMPLETED, Status.CANCELLED)
            )
            with st.expander(f"{t.title}  ·  {t.task_id}", expanded=False):
                st.markdown(
                    f"{priority_badge(t.priority.value)} {status_badge(t.status.value)}"
                    + (f" {badge('⏰ Overdue', 'b-error')}" if is_overdue else ""),
                    unsafe_allow_html=True,
                )
                st.markdown(f"**Description:** {t.description or '_No description_'}")
                cols = st.columns(2)
                cols[0].markdown(f"**Due Date:** {t.due_date or '—'}")
                cols[1].markdown(f"**Source:** {t.source}")
                cols2 = st.columns(2)
                cols2[0].markdown(f"**Created:** {t.created_date[:19].replace('T',' ')}")
                cols2[1].markdown(f"**Updated:** {t.updated_date[:19].replace('T',' ')}")
                if t.tags:
                    st.markdown("**Tags:** " + ", ".join(f"`{tag}`" for tag in t.tags))
                if t.notes:
                    st.caption(f"Notes: {t.notes}")

# ========================================================= REMINDERS TAB ==
with tab_reminders:
    reminders_all = reminder_repo.list()
    now_iso = datetime.now(timezone.utc).isoformat()
    today_str = date.today().isoformat()
    week_end = (datetime.now(timezone.utc).date().toordinal() + 7)

    rc1, rc2, rc3 = st.columns(3)
    upcoming_n = sum(1 for r in reminders_all if r.remind_at >= now_iso)
    past_n = sum(1 for r in reminders_all if r.remind_at < now_iso)
    rc1.markdown(stat_tile("Total Reminders", len(reminders_all)), unsafe_allow_html=True)
    rc2.markdown(stat_tile("Upcoming", upcoming_n), unsafe_allow_html=True)
    rc3.markdown(stat_tile("Past", past_n), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    fr1, fr2 = st.columns([2, 1])
    r_search = fr1.text_input("🔎 Search reminders", key="rem_search", placeholder="Search by title…")
    r_filter = fr2.selectbox("Filter", ["All", "Upcoming", "Past", "Today", "This Week"], key="rem_filter")

    reminders_sorted = sorted(reminders_all, key=lambda r: r.remind_at)
    filtered_r = reminders_sorted
    if r_search:
        rl = r_search.lower()
        filtered_r = [r for r in filtered_r if rl in r.title.lower()]
    if r_filter == "Upcoming":
        filtered_r = [r for r in filtered_r if r.remind_at >= now_iso]
    elif r_filter == "Past":
        filtered_r = [r for r in filtered_r if r.remind_at < now_iso]
    elif r_filter == "Today":
        filtered_r = [r for r in filtered_r if r.remind_at[:10] == today_str]
    elif r_filter == "This Week":
        filtered_r = [
            r for r in filtered_r
            if r.remind_at[:10] >= today_str
            and datetime.fromisoformat(r.remind_at[:10]).toordinal() <= week_end
        ]

    st.markdown("<br>", unsafe_allow_html=True)
    if not filtered_r:
        st.caption("No reminders match — ask the agent to set one in the Chat tab.")
    else:
        for r in filtered_r:
            is_upcoming = r.remind_at >= now_iso
            date_part = r.remind_at[:10] if len(r.remind_at) >= 10 else r.remind_at
            time_part = r.remind_at[11:16] if len(r.remind_at) >= 16 else "—"
            st.markdown(
                f"""<div class="pa-card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                        <div style="font-weight:700;font-size:1.02rem;">🔔 {r.title}</div>
                        <div style="color:var(--text-secondary);margin-top:4px;">📅 {date_part} &nbsp;·&nbsp; 🕐 {time_part}</div>
                        {"<div style='color:var(--text-secondary);margin-top:4px;'>Related Task: " + r.related_task_id + "</div>" if r.related_task_id else ""}
                        <div style="color:var(--text-secondary);margin-top:6px;font-size:0.78rem;">{r.reminder_id}</div>
                    </div>
                    <div>{badge("🔜 Upcoming", "b-waiting") if is_upcoming else badge("✔️ Past", "b-neutral")}</div>
                </div>
                </div>""",
                unsafe_allow_html=True,
            )

# ============================================================ NOTES TAB ==
with tab_notes:
    notes_all = note_repo.list()
    categories = sorted({n.category for n in notes_all})

    nc1, nc2, nc3 = st.columns(3)
    nc1.markdown(stat_tile("Total Notes", len(notes_all)), unsafe_allow_html=True)
    nc2.markdown(stat_tile("Categories", len(categories)), unsafe_allow_html=True)
    recent_notes = sum(1 for n in notes_all if n.created_date[:10] == _today_iso)
    nc3.markdown(stat_tile("Recent (Today)", recent_notes), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    fn1, fn2, fn3 = st.columns([2, 1, 1])
    n_search = fn1.text_input("🔎 Search notes", key="note_search", placeholder="Search by title or content…")
    n_cat = fn2.selectbox("Category", ["All"] + categories, key="note_cat")
    all_note_tags = sorted({tag for n in notes_all for tag in n.tags})
    n_tag = fn3.selectbox("Tag", ["All"] + all_note_tags, key="note_tag")

    filtered_notes = notes_all
    if n_search:
        nl = n_search.lower()
        filtered_notes = [n for n in filtered_notes if nl in n.title.lower() or nl in n.content.lower()]
    if n_cat != "All":
        filtered_notes = [n for n in filtered_notes if n.category == n_cat]
    if n_tag != "All":
        filtered_notes = [n for n in filtered_notes if n_tag in n.tags]

    st.markdown("<br>", unsafe_allow_html=True)
    if not filtered_notes:
        st.caption("No notes match — ask the agent to save one in the Chat tab.")
    else:
        for n in filtered_notes:
            preview = (n.content[:160] + "…") if len(n.content) > 160 else n.content
            st.markdown(
                f"""<div class="pa-card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div style="font-weight:700;font-size:1.02rem;">{n.title}</div>
                    {badge(n.category, "b-neutral")}
                </div>
                <div style="color:var(--text-secondary);margin-top:6px;font-size:0.85rem;">
                    Created {n.created_date[:10]} · Updated {n.updated_date[:10]}
                </div>
                <div style="margin-top:10px;">{preview}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            if n.tags:
                st.caption("Tags: " + ", ".join(f"`{tag}`" for tag in n.tags))
            with st.expander("Read more"):
                st.write(n.content)
                st.caption(f"Note ID: {n.note_id}")

# ============================================================= LOG TAB ==
with tab_logs:
    st.caption(
        "Every agent run is logged here: tools called, arguments, results, "
        "approval status, errors, and timing. No API keys or chain-of-thought are stored."
    )
    logs = log_repo.list_recent(50)
    if not logs:
        st.caption("No runs yet.")
    else:
        header_cols = st.columns([2, 1.3, 1.3, 1, 1.2, 1.2, 2])
        for c, h in zip(header_cols, ["Run ID", "Model", "Tools", "Duration", "Approval", "Status", "Timestamp"]):
            c.markdown(f"**{h}**")
        st.markdown("<hr style='margin:4px 0 10px 0;'>", unsafe_allow_html=True)

        for log in logs:
            tool_names = ", ".join(sorted({tc.tool_name for tc in log.tool_calls})) or "—"
            approval_terms = {tc.approval_status for tc in log.tool_calls if tc.approval_status}
            approval_label = ", ".join(sorted(approval_terms)) if approval_terms else "n/a"

            outcome = (log.stop_reason or log.final_outcome or "in progress").lower()
            if log.errors or "fail" in outcome or "error" in outcome:
                status_cls, status_lbl = "b-error", "Failed"
            elif "pending" in outcome or "approval" in outcome:
                status_cls, status_lbl = "b-waiting", "Approval Pending"
            elif "progress" in outcome or "running" in outcome:
                status_cls, status_lbl = "b-thinking", "Running"
            else:
                status_cls, status_lbl = "b-completed", "Completed"

            row_cols = st.columns([2, 1.3, 1.3, 1, 1.2, 1.2, 2])
            row_cols[0].markdown(f"`{log.run_id}`")
            row_cols[1].markdown(log.selected_model)
            row_cols[2].markdown(tool_names)
            row_cols[3].markdown(f"{log.total_duration_seconds or 0:.2f}s" if log.total_duration_seconds else "—")
            row_cols[4].markdown(approval_label)
            row_cols[5].markdown(badge(status_lbl, status_cls), unsafe_allow_html=True)
            row_cols[6].markdown(log.start_time[:19].replace("T", " "))

            with st.expander("Details"):
                st.markdown(f"**Request:** {log.user_request}")
                st.markdown(f"**Model:** {log.selected_model} · **Steps used:** {log.agent_steps_used}")
                if log.total_duration_seconds is not None:
                    st.markdown(f"**Execution Time:** {log.total_duration_seconds}s")
                if log.final_outcome:
                    st.markdown(f"**Final outcome:** {log.final_outcome}")
                if log.errors:
                    st.error("Errors: " + "; ".join(log.errors))
                if log.tool_calls:
                    st.markdown("**Tool calls:**")
                    for tc in log.tool_calls:
                        st.json({
                            "tool": tc.tool_name,
                            "arguments": tc.arguments,
                            "approval_required": tc.approval_required,
                            "approval_status": tc.approval_status,
                            "result": tc.result,
                            "error": tc.error,
                            "retry_count": tc.retry_count,
                            "duration_seconds": tc.duration_seconds,
                        })
            st.markdown("<hr style='margin:4px 0 10px 0;opacity:0.4;'>", unsafe_allow_html=True)
