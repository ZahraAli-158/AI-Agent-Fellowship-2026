"""Shared sidebar shell for every feature page: logo, workspace switcher,
primary navigation, and pinned/recent conversations. Streamlit's default
auto-generated page list is hidden via CSS so this custom nav is the only
one shown, keeping the enterprise-app feel consistent everywhere.
"""
from __future__ import annotations

import streamlit as st

from api_client import get
from components import gradient_divider
from theme import inject_theme

NAV_ITEMS = [
    ("🏠", "Dashboard", "pages/1_Dashboard.py"),
    ("💬", "Chat", "pages/2_Chat.py"),
    ("📚", "Knowledge Base", "pages/3_Knowledge_Base.py"),
    ("🧠", "Memory", "pages/4_Memory.py"),
    ("📝", "Prompt Library", "pages/5_Prompt_Library.py"),
    ("⚡", "AI Skills", "pages/6_AI_Skills.py"),
    ("🤖", "Assistant Settings", "pages/7_Assistant_Settings.py"),
]


def require_workspace():
    """Call at the top of every feature page. Injects theme, hides the
    default Streamlit page nav, and stops the page early with a friendly
    message if the user isn't logged in / hasn't picked a workspace yet."""
    st.set_page_config(page_title="AI Workspace Platform", page_icon="🧠", layout="wide")
    inject_theme()
    st.markdown("""
    <style>
    div[data-testid="stSidebarNav"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.get("token"):
        st.warning("Please sign in from the home page first.")
        st.page_link("app.py", label="← Back to Sign In")
        st.stop()
    if not st.session_state.get("workspace_id"):
        st.warning("Please select a workspace from the home page first.")
        st.page_link("app.py", label="← Back to Workspaces")
        st.stop()

    render_sidebar()


def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="display:flex; align-items:center; gap:10px; padding: 4px 0 14px 0;">
            <div style="width:32px; height:32px; border-radius:9px;
                        background:linear-gradient(135deg,#8B5CF6,#A855F7);
                        display:flex; align-items:center; justify-content:center; font-size:16px;
                        box-shadow:0 0 16px rgba(139,92,246,0.5);">🧠</div>
            <div style="font-weight:800; font-size:15px;">AI Workspace</div>
        </div>
        """, unsafe_allow_html=True)

        # --- Workspace switcher ---
        workspaces = get("/api/workspaces")
        names = {w["name"]: w["id"] for w in workspaces}
        current_name = st.session_state.get("workspace_name")
        if names:
            options = list(names.keys())
            idx = options.index(current_name) if current_name in options else 0
            chosen = st.selectbox("WORKSPACE", options, index=idx, label_visibility="visible")
            if chosen != current_name:
                st.session_state.workspace_id = names[chosen]
                st.session_state.workspace_name = chosen
                st.rerun()

        st.toggle("🌙 Dark Mode", key="dark_mode")

        gradient_divider()

        st.page_link("app.py", label="🏠  All Workspaces / Create New")

        gradient_divider()

        st.caption("NAVIGATION")
        for icon, label, target in NAV_ITEMS:
            st.page_link(target, label=f"{icon}  {label}")

        gradient_divider()

        st.caption("CONVERSATIONS")
        try:
            convos = get(f"/api/workspaces/{st.session_state.workspace_id}/conversations")
        except Exception:
            convos = []
        pinned = [c for c in convos if c.get("title", "").startswith("📌")]
        recent = convos[:5]
        if recent:
            for c in recent:
                title = c["title"][:28] + ("…" if len(c["title"]) > 28 else "")
                if st.button(f"🗂 {title}", key=f"nav_convo_{c['id']}", use_container_width=True):
                    st.session_state.active_conversation_id = c["id"]
                    st.switch_page("pages/2_Chat.py")
        else:
            st.caption("No conversations yet")

        gradient_divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.workspace_id = None
            st.switch_page("app.py")
