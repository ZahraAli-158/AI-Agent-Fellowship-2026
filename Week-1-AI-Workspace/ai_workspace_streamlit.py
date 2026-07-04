"""
AI Workspace — Streamlit version
A unified interface for interacting with the Gemini API.

"""

import os
import time
import uuid
import json
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # reads GEMINI_API_KEY from a local .env file, if present

# ---------------------------------------------------------------------------
# Config & constants
# ---------------------------------------------------------------------------

st.set_page_config(page_title="AI Workspace", page_icon="◈", layout="wide")

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Local file used to persist chats + API key between runs.
# NOTE: the API key is stored in plain text on your own computer only —
# never commit this file or share it, since anyone with it could use your key.
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_workspace_data.json")

MODEL_OPTIONS = {
    "gemini-2.5-flash": "Gemini 2.5 Flash — balanced, free tier",
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash-Lite — fastest, free tier",
}

BUILTIN_TEMPLATES = [
    ("📝", "Summarize Text", "Summarize the following text in a few clear bullet points:\n\n[paste your text here]"),
    ("🧩", "Explain Code", "Explain what the following code does, step by step, in plain language:\n\n[paste your code here]"),
    ("💡", "Generate Ideas", "Generate 10 creative ideas for:\n\n[describe your topic here]"),
    ("✍️", "Rewrite Content", "Rewrite the following content to be clearer and more concise, keeping the same meaning:\n\n[paste your content here]"),
    ("🌐", "Translate", "Translate the following text into [target language]:\n\n[paste your text here]"),
    ("📧", "Create Email", "Write a professional email about the following, with a subject line:\n\n[describe the purpose and key points here]"),
    ("🧠", "Brainstorm", "Let's brainstorm. Ask me clarifying questions first, then help me explore options for:\n\n[describe your problem here]"),
]

SYSTEM_PRESETS = {
    "Software engineer": "You are a professional software engineer. Answer with precise, production-quality reasoning and code.",
    "Research assistant": "You are an AI research assistant. Be thorough, cite tradeoffs, and stay evidence-based.",
    "Writing coach": "You are a friendly writing coach. Give concise, encouraging, actionable feedback.",
    "Clear": "",
}


# ---------------------------------------------------------------------------
# Disk persistence
# ---------------------------------------------------------------------------

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_data():
    payload = {
        "sessions": st.session_state.sessions,
        "active_id": st.session_state.active_id,
        "custom_templates": st.session_state.custom_templates,
        "api_key": st.session_state.api_key,
    }
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def new_session():
    sid = str(uuid.uuid4())[:8]
    st.session_state.sessions[sid] = {
        "title": "New chat",
        "model": "gemini-2.5-flash",
        "system_prompt": "",
        "threads": {"General": []},  # thread_name -> list of {role, content, response_time, tokens}
        "active_thread": "General",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    st.session_state.active_id = sid


if "sessions" not in st.session_state:
    _loaded = load_data()
    if _loaded.get("sessions"):
        st.session_state.sessions = _loaded["sessions"]
        st.session_state.active_id = _loaded.get("active_id") or next(iter(st.session_state.sessions))
        # Backward compatibility: upgrade any old-format session (flat "messages" list)
        # to the new "threads" structure so older saved data still loads correctly.
        for sess in st.session_state.sessions.values():
            if "threads" not in sess:
                sess["threads"] = {"General": sess.pop("messages", [])}
                sess["active_thread"] = "General"
    else:
        st.session_state.sessions = {}
        new_session()
    st.session_state.custom_templates = _loaded.get("custom_templates", [])
    st.session_state.api_key = _loaded.get("api_key") or os.getenv("GEMINI_API_KEY", "")

if "prompt_draft" not in st.session_state:
    st.session_state.prompt_draft = ""

# Clearing a widget-bound key must happen BEFORE that widget is instantiated
# in this run, so we use a flag set on submit and consumed here.
if st.session_state.get("_clear_prompt_draft"):
    st.session_state.prompt_draft = ""
    st.session_state._clear_prompt_draft = False


def apply_template(thread_name: str, text: str):
    s = active_session()
    if thread_name not in s["threads"]:
        s["threads"][thread_name] = []
    s["active_thread"] = thread_name
    st.session_state.prompt_draft = text


def active_session():
    return st.session_state.sessions[st.session_state.active_id]


def active_messages():
    s = active_session()
    if s["active_thread"] not in s["threads"]:
        s["threads"][s["active_thread"]] = []
    return s["threads"][s["active_thread"]]


def estimate_tokens(text: str) -> int:
    return max(1, -(-len(text or "") // 4))  # ceil division


# ---------------------------------------------------------------------------
# Sidebar — sessions, API key, export
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### ◈ AI Workspace")

    if st.button("＋ New chat", use_container_width=True):
        new_session()
        st.rerun()

    st.markdown("---")
    st.caption("Chat sessions")
    for sid, s in list(st.session_state.sessions.items()):
        cols = st.columns([5, 1])
        label = s["title"] if len(s["title"]) < 28 else s["title"][:27] + "…"
        btn_type = "primary" if sid == st.session_state.active_id else "secondary"
        if cols[0].button(label, key=f"switch_{sid}", use_container_width=True, type=btn_type):
            st.session_state.active_id = sid
            st.rerun()
        if cols[1].button("✕", key=f"del_{sid}"):
            del st.session_state.sessions[sid]
            if not st.session_state.sessions:
                new_session()
            elif st.session_state.active_id == sid:
                st.session_state.active_id = next(iter(st.session_state.sessions))
            st.rerun()

    st.markdown("---")
    st.caption("Gemini API key")
    st.session_state.api_key = st.text_input(
        "API key", value=st.session_state.api_key, type="password",
        placeholder="AIza...", label_visibility="collapsed",
    )
    st.caption("Free key: aistudio.google.com → Get API key. Saved locally in "
               "ai_workspace_data.json next to this script — don't share that file.")

    if st.button("🗑️ Clear saved history & key", use_container_width=True):
        st.session_state.sessions = {}
        new_session()
        st.session_state.custom_templates = []
        st.session_state.api_key = ""
        save_data()
        st.rerun()

    st.markdown("---")
    s = active_session()
    has_any_messages = any(s["threads"].values())
    if has_any_messages:
        export_lines = [f"# {s['title']}", "", f"Model: {MODEL_OPTIONS.get(s['model'], s['model'])}",
                         f"System prompt: {s['system_prompt'] or '(none)'}", "", "---"]
        for thread_name, msgs in s["threads"].items():
            if not msgs:
                continue
            export_lines.append(f"\n## {thread_name}\n")
            for m in msgs:
                who = "You" if m["role"] == "user" else "Assistant"
                export_lines.append(f"**{who}:**\n\n{m['content']}\n")
        st.download_button(
            "⇩ Export current chat",
            data="\n".join(export_lines),
            file_name=f"{s['title'][:30] or 'chat'}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    else:
        st.button("⇩ Export current chat", disabled=True, use_container_width=True)

    st.caption("Dark / light mode: use the ⋮ menu (top-right) → Settings → Theme.")


# ---------------------------------------------------------------------------
# Top bar — model, system prompt, stats
# ---------------------------------------------------------------------------

s = active_session()

top_l, top_m, top_r = st.columns([2, 2, 2])

with top_l:
    s["model"] = st.selectbox(
        "Model", options=list(MODEL_OPTIONS.keys()),
        format_func=lambda k: MODEL_OPTIONS[k],
        index=list(MODEL_OPTIONS.keys()).index(s["model"]),
        key=f"model_select_{st.session_state.active_id}",
    )

with top_m:
    total_tokens = estimate_tokens(s["system_prompt"])
    for msgs in s["threads"].values():
        total_tokens += sum(estimate_tokens(m["content"]) for m in msgs)
    st.metric("Tokens (est.)", total_tokens)

with top_r:
    current_msgs = active_messages()
    last = next((m for m in reversed(current_msgs) if m["role"] == "assistant" and "response_time" in m), None)
    st.metric("Last response", f"{last['response_time']} ms" if last else "—")

with st.expander("✎ System prompt"):
    preset_cols = st.columns(len(SYSTEM_PRESETS))
    for i, (name, body) in enumerate(SYSTEM_PRESETS.items()):
        if preset_cols[i].button(name, key=f"preset_{name}_{st.session_state.active_id}"):
            s["system_prompt"] = body
            st.rerun()
    s["system_prompt"] = st.text_area(
        "Custom system prompt", value=s["system_prompt"], height=80,
        placeholder="e.g. You are a professional software engineer.",
        key=f"sysprompt_{st.session_state.active_id}",
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Prompt templates row
# ---------------------------------------------------------------------------

st.caption("Templates")
tmpl_cols = st.columns(len(BUILTIN_TEMPLATES))
for i, (icon, name, body) in enumerate(BUILTIN_TEMPLATES):
    tmpl_cols[i].button(
        f"{icon} {name}", key=f"tmpl_{name}",
        on_click=apply_template, args=(name, body),
        use_container_width=True,
    )

if st.session_state.custom_templates:
    st.caption("Your saved templates")
    ccols = st.columns(len(st.session_state.custom_templates))
    for i, (name, body) in enumerate(st.session_state.custom_templates):
        ccols[i].button(f"⭐ {name}", key=f"ctmpl_{i}", on_click=apply_template, args=(name, body), use_container_width=True)

with st.expander("💾 Save current text as a template"):
    with st.form("save_template_form", clear_on_submit=True):
        t_name = st.text_input("Template name")
        t_body = st.text_area("Template text", value=st.session_state.prompt_draft)
        if st.form_submit_button("Save template"):
            if t_name.strip() and t_body.strip():
                st.session_state.custom_templates.append((t_name.strip(), t_body.strip()))
                st.success(f"Saved template '{t_name}'")

# ---------------------------------------------------------------------------
# Thread tabs — each template gets its own separate conversation thread,
# so answers from different templates never mix together.
# ---------------------------------------------------------------------------

thread_names = list(s["threads"].keys())
st.caption("Threads (answers from each stay separate)")
thread_cols = st.columns(len(thread_names))
for i, tname in enumerate(thread_names):
    count = len(s["threads"][tname])
    label = f"{'💬' if tname == 'General' else '📌'} {tname}" + (f" ({count})" if count else "")
    btn_type = "primary" if tname == s["active_thread"] else "secondary"
    if thread_cols[i].button(label, key=f"thread_{tname}_{st.session_state.active_id}", use_container_width=True, type=btn_type):
        s["active_thread"] = tname
        st.rerun()

st.markdown("---")

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

chat_container = st.container()
with chat_container:
    current_msgs = active_messages()
    if not current_msgs:
        empty_title = "Start a conversation" if s["active_thread"] == "General" else f'"{s["active_thread"]}" thread'
        empty_sub = ("Pick a template above, set a system prompt, or just type your question below."
                     if s["active_thread"] == "General" else
                     "This template has its own thread — send a message to start it.")
        st.markdown(
            f"<div style='text-align:center; color:#888; padding:60px 0;'>"
            f"<div style='font-size:32px;'>◈</div>"
            f"<h4>{empty_title}</h4>"
            f"<p>{empty_sub}</p>"
            f"</div>", unsafe_allow_html=True,
        )
    for m in current_msgs:
        avatar = "🧑" if m["role"] == "user" else "🤖"
        with st.chat_message(m["role"], avatar=avatar):
            if m.get("error"):
                st.error(m["content"])
            else:
                st.markdown(m["content"])
                if m["role"] == "assistant" and "response_time" in m:
                    st.caption(f"{MODEL_OPTIONS.get(s['model'], s['model'])} · {m['response_time']}ms · ~{m.get('tokens', 0)} tok")

# ---------------------------------------------------------------------------
# Input area
# ---------------------------------------------------------------------------

with st.form("prompt_form", clear_on_submit=False):
    prompt_text = st.text_area(
        "Message", key="prompt_draft", height=90,
        placeholder="Ask anything, or pick a template above...",
        label_visibility="collapsed",
    )
    send_col, warn_col = st.columns([1, 5])
    submitted = send_col.form_submit_button("➤ Send", use_container_width=True)

if submitted:
    text = (prompt_text or "").strip()

    if not text:
        st.warning("Please enter a message before sending.")
    elif not st.session_state.api_key:
        st.error('No Gemini API key set yet. Paste your key in the sidebar under "Gemini API key" to start chatting.')
    else:
        msgs = active_messages()
        if s["title"] == "New chat":
            s["title"] = text[:40] + ("…" if len(text) > 40 else "")

        msgs.append({"role": "user", "content": text})

        gemini_contents = [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in msgs
        ]
        body = {"contents": gemini_contents}
        if s["system_prompt"]:
            body["system_instruction"] = {"parts": [{"text": s["system_prompt"]}]}

        endpoint = GEMINI_ENDPOINT.format(model=s["model"])
        headers = {"Content-Type": "application/json", "x-goog-api-key": st.session_state.api_key}

        start = time.time()
        try:
            with st.spinner("Waiting for Gemini..."):
                resp = requests.post(endpoint, headers=headers, data=json.dumps(body), timeout=60)
            elapsed_ms = int((time.time() - start) * 1000)

            if not resp.ok:
                reason = "Connection failed. Please check your network and try again."
                if resp.status_code in (400, 401, 403):
                    reason = "Invalid API key. Please check the key in the sidebar and try again."
                elif resp.status_code == 429:
                    reason = "Rate limit reached (free tier has daily/per-minute limits). Please wait and try again."
                elif resp.status_code >= 500:
                    reason = "The AI service is temporarily unavailable. Please try again shortly."
                try:
                    err_json = resp.json()
                    msg = err_json.get("error", {}).get("message")
                    if msg:
                        reason += f" ({msg})"
                except Exception:
                    pass
                msgs.append({"role": "assistant", "content": reason, "error": True})
            else:
                data = resp.json()
                candidates = data.get("candidates", [])
                reply = ""
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    reply = "".join(p.get("text", "") for p in parts)
                if not reply:
                    reply = "_(no response text returned)_"
                tokens = data.get("usageMetadata", {}).get("candidatesTokenCount", estimate_tokens(reply))
                msgs.append({
                    "role": "assistant", "content": reply,
                    "response_time": elapsed_ms, "tokens": tokens,
                })
        except requests.exceptions.RequestException:
            msgs.append({
                "role": "assistant",
                "content": "Connection failed — could not reach generativelanguage.googleapis.com. Check your network and try again.",
                "error": True,
            })

        st.session_state._clear_prompt_draft = True
        save_data()
        st.rerun()

# Persist everything (sessions, templates, API key) at the end of every run,
# so closing and reopening the app restores where you left off.
save_data()
