import streamlit as st

from api_client import delete, get, patch, post, put
from components import badge, empty_state, gradient_divider, page_header
from nav import require_workspace

require_workspace()
ws_id = st.session_state.workspace_id

page_header("🧠", "Long-Term Memory", "Curate what your assistant remembers across sessions")
gradient_divider()

CATEGORY_COLORS = {"preference": "blue", "pinned": "purple", "discussion": "green", "faq": "yellow", "general": "purple"}

with st.container(border=True):
    st.markdown("#### Add Memory")
    with st.form("new_memory"):
        col1, col2 = st.columns([1, 3])
        with col1:
            category = st.selectbox("Category", ["preference", "pinned", "discussion", "faq", "general"])
        with col2:
            content = st.text_area("Content", height=80, placeholder="e.g. User prefers concise answers")
        pinned = st.checkbox("📌 Pin this item")
        if st.form_submit_button("Save Memory", use_container_width=True):
            post(f"/api/workspaces/{ws_id}/memory", json={"category": category, "content": content, "pinned": pinned})
            st.rerun()

gradient_divider()

search = st.text_input("🔍 Search memory", placeholder="Filter by keyword…")
items = get(f"/api/workspaces/{ws_id}/memory")
if search:
    items = [i for i in items if search.lower() in i["content"].lower()]

st.markdown("#### Stored Memory")
if not items:
    empty_state("🧠", "No memory items", "Add preferences, facts, or pinned notes above")
for item in items:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
        with c1:
            pin_icon = "📌 " if item["pinned"] else ""
            st.markdown(f"{pin_icon}{badge(item['category'], CATEGORY_COLORS.get(item['category'], 'purple'))}",
                        unsafe_allow_html=True)
            st.markdown(item["content"])
            st.markdown(f"<span class='awp-muted' style='font-size:11px;'>{item['created_at'][:10]}</span>",
                        unsafe_allow_html=True)
        with c2:
            if st.button("📌", key=f"pin_{item['id']}", help="Pin/Unpin", use_container_width=True):
                patch(f"/api/workspaces/{ws_id}/memory/{item['id']}/pin")
                st.rerun()
        with c3:
            if st.button("✏️", key=f"edit_{item['id']}", help="Edit", use_container_width=True):
                st.session_state[f"editing_mem_{item['id']}"] = not st.session_state.get(f"editing_mem_{item['id']}", False)
        with c4:
            if st.button("🗑️", key=f"del_{item['id']}", help="Delete", use_container_width=True):
                delete(f"/api/workspaces/{ws_id}/memory/{item['id']}")
                st.rerun()

        if st.session_state.get(f"editing_mem_{item['id']}"):
            with st.form(f"edit_mem_form_{item['id']}"):
                new_cat = st.selectbox("Category", ["preference", "pinned", "discussion", "faq", "general"],
                                        index=["preference", "pinned", "discussion", "faq", "general"].index(item["category"])
                                        if item["category"] in ["preference", "pinned", "discussion", "faq", "general"] else 0,
                                        key=f"cat_edit_{item['id']}")
                new_content = st.text_area("Content", value=item["content"], key=f"content_edit_{item['id']}")
                new_pinned = st.checkbox("📌 Pinned", value=item["pinned"], key=f"pinned_edit_{item['id']}")
                ec1, ec2 = st.columns(2)
                with ec1:
                    if st.form_submit_button("Save", use_container_width=True):
                        put(f"/api/workspaces/{ws_id}/memory/{item['id']}",
                            json={"category": new_cat, "content": new_content, "pinned": new_pinned})
                        del st.session_state[f"editing_mem_{item['id']}"]
                        st.rerun()
                with ec2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        del st.session_state[f"editing_mem_{item['id']}"]
                        st.rerun()
