import html as _html
import json as _json

import streamlit as st
import streamlit.components.v1 as components

from api_client import get, get_raw, patch, post
from components import empty_state, gradient_divider, page_header
from nav import require_workspace

require_workspace()
ws_id = st.session_state.workspace_id

page_header("💬", "Chat", "Talk to your configured assistants, grounded in your documents")

assistants = get(f"/api/workspaces/{ws_id}/assistants")
if not assistants:
    gradient_divider()
    empty_state("🤖", "No assistants configured", "Create one in Assistant Settings to start chatting")
    if st.button("Go to Assistant Settings"):
        st.switch_page("pages/7_Assistant_Settings.py")
    st.stop()

names = {a["name"]: a for a in assistants}
default_name = st.session_state.get("active_assistant_name", list(names.keys())[0])
if default_name not in names:
    default_name = list(names.keys())[0]

top_l, top_r = st.columns([3, 2])
with top_l:
    chosen_name = st.selectbox("Assistant", list(names.keys()),
                                index=list(names.keys()).index(default_name))
    assistant = names[chosen_name]
with top_r:
    st.markdown(
        f"<div class='awp-muted' style='padding-top:28px;'>Model: <b style='color:#A855F7'>{assistant['model']}</b>"
        f" · Temp: {assistant['temperature']} · Style: {assistant['response_style']}</div>",
        unsafe_allow_html=True,
    )

gradient_divider()

# --- Sidebar-local: conversation list scoped to this page ---
with st.sidebar:
    st.caption("THIS ASSISTANT'S CHATS")
    search = st.text_input("🔍 Search conversations", label_visibility="collapsed", placeholder="Search conversations…")
    params = {"search": search} if search else {}
    conversations = get(f"/api/workspaces/{ws_id}/conversations", params=params)

    if st.button("➕ New Conversation", use_container_width=True):
        convo = post(f"/api/workspaces/{ws_id}/conversations",
                      json={"assistant_id": assistant["id"]})
        st.session_state.active_conversation_id = convo["id"]
        st.rerun()

    for c in conversations:
        label = ("📌 " if c["title"].startswith("📌") else "🗂 ") + c["title"][:26]
        if st.button(label, key=f"chatpage_convo_{c['id']}", use_container_width=True):
            st.session_state.active_conversation_id = c["id"]
            st.rerun()

convo_id = st.session_state.get("active_conversation_id")
if not convo_id:
    empty_state("💬", "No conversation selected", "Start a new conversation from the sidebar")
    st.stop()

messages = get(f"/api/workspaces/{ws_id}/conversations/{convo_id}/messages")


def _speak_button(text: str, key: str) -> None:
    """Speech Output: uses the browser's native Web Speech API
    (speechSynthesis) to read a message aloud. No external API/key needed."""
    safe_text = _json.dumps(text)
    components.html(f"""
        <button onclick='
            const u = new SpeechSynthesisUtterance({safe_text});
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(u);
        ' style="
            background: linear-gradient(135deg,#8B5CF6,#A855F7); color:white; border:none;
            border-radius:8px; padding:4px 10px; font-size:12px; cursor:pointer;
        ">🔊 Speak</button>
    """, height=36)


chat_container = st.container(height=420)
with chat_container:
    if not messages:
        empty_state("✨", "Say hello", "Send your first message below to begin")
    for m in messages:
        avatar = "🧑" if m["role"] == "user" else "🤖"
        with st.chat_message(m["role"], avatar=avatar):
            pin_mark = "📌 " if m.get("pinned") else ""
            st.markdown(f"{pin_mark}{m['content']}")
            if m["role"] == "assistant" and m.get("model_used"):
                st.caption(
                    f"🔹 {m['model_used']} · {m['provider_used']} · "
                    f"{m['input_tokens']}+{m['output_tokens']} tokens · "
                    f"{m.get('response_time_ms', 0)} ms"
                )
                bcol1, bcol2 = st.columns([1, 1])
                with bcol1:
                    if st.button("📌 Unpin" if m.get("pinned") else "📌 Pin", key=f"pinmsg_{m['id']}"):
                        patch(f"/api/workspaces/{ws_id}/conversations/{convo_id}/messages/{m['id']}/pin")
                        st.rerun()
                with bcol2:
                    _speak_button(m["content"], key=f"speak_{m['id']}")

gradient_divider()

with st.expander("📌 Pinned / Bookmarked Messages in this Workspace"):
    pinned_messages = get(f"/api/workspaces/{ws_id}/conversations/messages/pinned")
    if not pinned_messages:
        st.caption("No pinned messages yet. Pin any assistant reply above to bookmark it here.")
    for pm in pinned_messages:
        st.markdown(f"**{pm['role'].title()}:** {pm['content'][:200]}")
        st.caption(pm["created_at"][:19].replace("T", " "))

gradient_divider()

# --- Action row: export, pin conversation ---
act1, act2, act3 = st.columns(3)
with act1:
    if st.button("⬇️ Export Markdown", use_container_width=True):
        content = get_raw(f"/api/workspaces/{ws_id}/conversations/{convo_id}/export/markdown")
        st.download_button("Download .md", content, file_name="conversation.md", use_container_width=True)
with act2:
    if st.button("⬇️ Export PDF", use_container_width=True):
        content = get_raw(f"/api/workspaces/{ws_id}/conversations/{convo_id}/export/pdf")
        st.download_button("Download .pdf", content, file_name="conversation.pdf", use_container_width=True)
with act3:
    convo = next((c for c in conversations if c["id"] == convo_id), None)
    is_pinned = convo and convo["title"].startswith("📌")
    if st.button("📌 Unpin Conversation" if is_pinned else "📌 Pin Conversation", use_container_width=True):
        title = convo["title"] if convo else "Conversation"
        new_title = title[2:].strip() if is_pinned else f"📌 {title}"
        patch(f"/api/workspaces/{ws_id}/conversations/{convo_id}/rename", params={"title": new_title})
        st.rerun()

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
ground_in_docs = st.toggle("📎 Ground answers using uploaded documents", value=False)

# --- Voice Input ---
with st.expander("🎙️ Voice Input (records via your microphone, transcribed with OpenAI Whisper)"):
    audio = st.audio_input("Record a message")
    if audio is not None and st.button("Transcribe & Use as Message"):
        with st.spinner("Transcribing…"):
            try:
                files = {"file": ("voice.wav", audio.getvalue(), "audio/wav")}
                result = post(f"/api/workspaces/{ws_id}/voice/transcribe", files=files)
                st.session_state.prefill_prompt = result["text"]
                st.success(f"Transcribed: {result['text']}")
            except Exception as e:
                st.error(
                    "Transcription failed. Voice input requires OPENAI_API_KEY to be set in the "
                    "backend's .env file (uses OpenAI Whisper)."
                )

# --- Prefilled prompt from Prompt Library or Voice Input ---
# Root-cause fix: previously this used st.session_state.pop(...) here, which
# consumed the flag on the very first rerun. Since every widget interaction
# (typing in the box, clicking Send) triggers a full script rerun, the box
# and Send button -- both nested inside `if prefill:` -- vanished on the
# very next rerun before the click could ever be processed, silently
# dropping the message. Fix: keep the flag alive across reruns using
# `in st.session_state` (not pop), and only remove it explicitly in the
# success path, right after the SAME post() call normal chat uses.
if "prefill_prompt" in st.session_state:
    prefill = st.session_state["prefill_prompt"]
    st.markdown("<div class='awp-muted' style='font-size:13px;'>Loaded from Prompt Library / Voice Input — edit if needed, then send:</div>",
                unsafe_allow_html=True)
    edited = st.text_area("Prefilled message", value=prefill, height=90, key="prefill_editor")
    if st.button("➤ Send this message", use_container_width=True):
        with st.spinner("Thinking…"):
            post(f"/api/workspaces/{ws_id}/conversations/{convo_id}/chat", json={"message": edited})
        del st.session_state["prefill_prompt"]
        st.session_state.pop("prefill_editor", None)
        st.rerun()

prompt = st.chat_input("Message your assistant…")
if prompt:
    if ground_in_docs:
        with st.spinner("Retrieving relevant documents and answering…"):
            ask_result = post(f"/api/workspaces/{ws_id}/documents/ask", json={"question": prompt})
        with chat_container:
            with st.chat_message("user", avatar="🧑"):
                st.markdown(prompt)
            with st.chat_message("assistant", avatar="📎"):
                st.markdown(ask_result["answer"])
                if ask_result["sources"]:
                    st.caption("Sources: " + ", ".join(s["filename"] for s in ask_result["sources"]))
        st.info("This grounded answer used your documents directly and wasn't saved to conversation history. Turn off grounding to chat normally with persistent history.")
    else:
        with st.spinner("Thinking…"):
            post(f"/api/workspaces/{ws_id}/conversations/{convo_id}/chat", json={"message": prompt})
        st.rerun()
