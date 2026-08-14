import streamlit as st

from api_client import delete, get, patch, post
from components import badge, empty_state, gradient_divider, page_header
from nav import require_workspace

require_workspace()
ws_id = st.session_state.workspace_id

page_header("📝", "Prompt Library", "Save and reuse your best prompts")
gradient_divider()

CATEGORIES = ["writing", "programming", "research", "business", "education", "custom"]
CATEGORY_COLORS = {"writing": "purple", "programming": "blue", "research": "green",
                    "business": "yellow", "education": "purple", "custom": "red"}

with st.container(border=True):
    st.markdown("#### Create Prompt")
    with st.form("new_prompt"):
        title = st.text_input("Title", placeholder="Bug Report Template")
        category = st.selectbox("Category", CATEGORIES)
        content = st.text_area("Prompt content", height=120, placeholder="Describe the bug: {description}")
        if st.form_submit_button("Save Prompt", use_container_width=True):
            post(f"/api/workspaces/{ws_id}/prompts", json={"title": title, "category": category, "content": content})
            st.rerun()

gradient_divider()

filter_col, search_col, fav_col = st.columns([1, 2, 1])
with filter_col:
    filter_cat = st.selectbox("Filter", ["all"] + CATEGORIES)
with search_col:
    search = st.text_input("🔍 Search prompts", placeholder="Search by title…", label_visibility="visible")
with fav_col:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    favorites_only = st.checkbox("⭐ Favorites only")

params = {}
if filter_cat != "all":
    params["category"] = filter_cat
if favorites_only:
    params["favorites_only"] = True
prompts = get(f"/api/workspaces/{ws_id}/prompts", params=params)
if search:
    prompts = [p for p in prompts if search.lower() in p["title"].lower()]

st.markdown("#### Saved Prompts")
if not prompts:
    empty_state("📝", "No prompts yet", "Create your first reusable prompt template above")

cols = st.columns(2)
for i, p in enumerate(prompts):
    with cols[i % 2]:
        with st.container(border=True):
            star = "⭐ " if p.get("favorite") else ""
            st.markdown(f"{star}**{p['title']}**  " + badge(p["category"], CATEGORY_COLORS.get(p["category"], "purple")),
                        unsafe_allow_html=True)
            st.code(p["content"], language=None)
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                if st.button("💬 Use", key=f"use_{p['id']}", use_container_width=True,
                             help="Load this prompt into Chat"):
                    st.session_state.prefill_prompt = p["content"]
                    st.switch_page("pages/2_Chat.py")
            with b2:
                if st.button("⭐", key=f"fav_{p['id']}", use_container_width=True, help="Favorite/Unfavorite"):
                    patch(f"/api/workspaces/{ws_id}/prompts/{p['id']}/favorite")
                    st.rerun()
            with b3:
                if st.button("⧉", key=f"dup_{p['id']}", use_container_width=True, help="Duplicate"):
                    post(f"/api/workspaces/{ws_id}/prompts/{p['id']}/duplicate")
                    st.rerun()
            with b4:
                if st.button("🗑️", key=f"delp_{p['id']}", use_container_width=True, help="Delete"):
                    delete(f"/api/workspaces/{ws_id}/prompts/{p['id']}")
                    st.rerun()
