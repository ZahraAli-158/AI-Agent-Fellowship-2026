import streamlit as st

from api_client import get, post
from components import badge, empty_state, gradient_divider, page_header
from nav import require_workspace

require_workspace()
ws_id = st.session_state.workspace_id

page_header("🤖", "Assistant Settings", "Configure the AI assistants available in this workspace")
gradient_divider()

left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown("#### Configure New Assistant")
    with st.container(border=True):
        name = st.text_input("Assistant Name", value="My Assistant")
        role = st.text_input("Role", value="General Assistant")
        system_prompt = st.text_area("System Prompt", value="You are a helpful assistant.", height=100)

        c1, c2 = st.columns(2)
        with c1:
            model = st.text_input("Model (blank = server default)", value="", placeholder="gemini-2.5-flash")
            temperature = st.slider("Temperature", 0.0, 1.5, 0.7, help="Higher = more creative, lower = more focused")
            max_tokens = st.number_input("Max Tokens", min_value=64, max_value=8000, value=1024)
        with c2:
            personality = st.selectbox("Personality", ["neutral", "friendly", "formal", "witty"])
            response_style = st.selectbox("Response Style", ["concise", "detailed", "bullet-points"])
            creativity = st.slider("Creativity", 0.0, 1.0, 0.5, help="UI-only creative framing of temperature")

        b1, b2 = st.columns(2)
        with b1:
            create_clicked = st.button("💾 Save Assistant", use_container_width=True)
        with b2:
            if st.button("↺ Reset", use_container_width=True):
                st.rerun()

        if create_clicked:
            post(f"/api/workspaces/{ws_id}/assistants", json={
                "name": name, "role": role, "system_prompt": system_prompt,
                "model": model or None, "temperature": temperature, "max_tokens": int(max_tokens),
                "personality": personality, "response_style": response_style,
            })
            st.success(f"Assistant '{name}' created.")
            st.rerun()

with right:
    st.markdown("#### Live Preview")
    with st.container(border=True):
        st.markdown(f"### 🤖 {name or 'Unnamed Assistant'}")
        st.markdown(badge(role or "General Assistant", "purple"), unsafe_allow_html=True)
        st.markdown(f"<div class='awp-muted' style='margin-top:10px; font-size:13px;'>{system_prompt}</div>",
                    unsafe_allow_html=True)
        gradient_divider()
        st.markdown(
            f"**Model:** {model or 'server default'}  \n"
            f"**Temperature:** {temperature}  \n"
            f"**Max Tokens:** {int(max_tokens)}  \n"
            f"**Personality:** {personality}  \n"
            f"**Style:** {response_style}"
        )

gradient_divider()

st.markdown("#### Existing Assistants")
assistants = get(f"/api/workspaces/{ws_id}/assistants")
if not assistants:
    empty_state("🤖", "No assistants yet", "Configure your first assistant above")

cols = st.columns(2)
for i, a in enumerate(assistants):
    with cols[i % 2]:
        with st.container(border=True):
            st.markdown(f"**{a['name']}**  " + badge(a["model"], "blue"), unsafe_allow_html=True)
            st.markdown(f"<span class='awp-muted' style='font-size:13px;'>{a['system_prompt']}</span>",
                        unsafe_allow_html=True)
            st.caption(f"temp={a['temperature']} · max_tokens={a['max_tokens']} · {a['response_style']}")
            if st.button(f"💬 Chat with {a['name']}", key=f"chat_{a['id']}", use_container_width=True):
                st.session_state.active_assistant_id = a["id"]
                st.session_state.active_assistant_name = a["name"]
                st.switch_page("pages/2_Chat.py")
