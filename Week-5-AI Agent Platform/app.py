"""AI Workspace Platform — Streamlit frontend entrypoint.
Premium dark purple-glassmorphism shell: handles auth and workspace
selection/creation. Feature pages live in frontend/pages/*.py.
"""
from __future__ import annotations

import requests
import streamlit as st

from api_client import delete, get, login, patch, post, register
from components import empty_state, gradient_divider, page_header
from theme import inject_theme

st.set_page_config(page_title="AI Workspace Platform", page_icon="🧠", layout="wide")

# --- Session state defaults ---
for key, default in [
    ("token", None), ("user_email", None), ("workspace_id", None), ("workspace_name", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

inject_theme()  # also initializes/syncs dark_mode from the URL (see theme.py)


def _logo_block():
    st.markdown("""
    <div style="display:flex; align-items:center; gap:10px; padding: 4px 0 18px 0;">
        <div style="width:36px; height:36px; border-radius:10px;
                    background:linear-gradient(135deg,#8B5CF6,#A855F7);
                    display:flex; align-items:center; justify-content:center; font-size:18px;
                    box-shadow:0 0 20px rgba(139,92,246,0.5);">🧠</div>
        <div style="font-weight:800; font-size:17px;">AI Workspace</div>
    </div>
    """, unsafe_allow_html=True)


if not st.session_state.token:
    # --- Centered auth panel ---
    col_l, col_mid, col_r = st.columns([1, 1.3, 1])
    with col_mid:
        st.markdown("<div style='height:64px'></div>", unsafe_allow_html=True)
        _logo_block()
        st.markdown("""
        <h1 style="font-size:34px; margin-bottom:0;">Welcome back</h1>
        <p class="awp-muted" style="margin-top:4px;">Sign in to your premium AI workspace</p>
        """, unsafe_allow_html=True)
        gradient_divider()

        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        with tab_login:
            email = st.text_input("Email", key="login_email", placeholder="you@company.com")
            password = st.text_input("Password", type="password", key="login_password", placeholder="••••••••")
            if st.button("Sign In", use_container_width=True):
                try:
                    token = login(email, password)
                    st.session_state.token = token
                    st.session_state.user_email = email
                    st.rerun()
                except requests.HTTPError:
                    st.error("Invalid email or password.")

        with tab_register:
            r_name = st.text_input("Full Name", key="reg_name", placeholder="Lily Ahmed")
            r_email = st.text_input("Email", key="reg_email", placeholder="you@company.com")
            r_password = st.text_input("Password", type="password", key="reg_password",
                                        placeholder="At least 8 characters")
            if st.button("Create Account", use_container_width=True):
                try:
                    register(r_email, r_password, r_name)
                    st.success("Account created — switch to Sign In.")
                except requests.HTTPError as e:
                    try:
                        detail = e.response.json().get("detail", str(e))
                    except Exception:
                        detail = str(e)
                    st.error(f"Registration failed: {detail}")

else:
    # --- Sidebar shell ---
    with st.sidebar:
        _logo_block()
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:8px; padding:10px 12px; border-radius:10px;
                    background:#111118; border:1px solid rgba(255,255,255,0.08); margin-bottom:16px;">
            <div style="width:28px;height:28px;border-radius:50%;
                        background:linear-gradient(135deg,#8B5CF6,#A855F7);
                        display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;">
                {st.session_state.user_email[:1].upper()}
            </div>
            <div style="font-size:13px; color:#B8B8C7;">{st.session_state.user_email}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.workspace_id = None
            st.rerun()

        gradient_divider()
        st.caption("WORKSPACES")

    page_header("🧠", "AI Workspace Platform", "Manage your AI-powered workspaces")
    gradient_divider()

    show_archived = st.checkbox("Show archived workspaces")
    workspaces = get("/api/workspaces", params={"include_archived": True} if show_archived else {})
    if not show_archived:
        workspaces = [w for w in workspaces if not w.get("archived")]

    col1, col2 = st.columns([2, 1], gap="large")
    with col1:
        st.markdown("#### Your Workspaces")
        if workspaces:
            for w in workspaces:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([4, 1, 1])
                    with c1:
                        archived_tag = " · 🗄️ Archived" if w.get("archived") else ""
                        st.markdown(f"**{w['name']}**{archived_tag}")
                        if w.get("description"):
                            st.markdown(f"<span class='awp-muted'>{w['description']}</span>", unsafe_allow_html=True)
                        try:
                            stats = get(f"/api/workspaces/{w['id']}/stats")
                            st.caption(
                                f"💬 {stats['conversations']} conversations · 📄 {stats['documents']} documents · "
                                f"👥 {stats['members']} member(s)"
                            )
                        except Exception:
                            pass
                    with c2:
                        if st.button("Open →", key=f"open_{w['id']}", use_container_width=True):
                            st.session_state.workspace_id = w["id"]
                            st.session_state.workspace_name = w["name"]
                            st.switch_page("pages/1_Dashboard.py")
                    with c3:
                        if st.button("⋯", key=f"more_{w['id']}", help="More options", use_container_width=True):
                            st.session_state[f"show_options_{w['id']}"] = not st.session_state.get(f"show_options_{w['id']}", False)

                    if st.session_state.get(f"show_options_{w['id']}"):
                        oc1, oc2, oc3, oc4 = st.columns(4)
                        with oc1:
                            if st.button("✏️ Edit", key=f"edit_{w['id']}", use_container_width=True):
                                st.session_state[f"editing_{w['id']}"] = True
                        with oc2:
                            if st.button("⧉ Clone", key=f"clone_{w['id']}", use_container_width=True):
                                post(f"/api/workspaces/{w['id']}/clone")
                                st.success("Workspace cloned.")
                                st.rerun()
                        with oc3:
                            archive_label = "📤 Unarchive" if w.get("archived") else "🗄️ Archive"
                            if st.button(archive_label, key=f"archive_{w['id']}", use_container_width=True):
                                patch(f"/api/workspaces/{w['id']}/archive")
                                st.rerun()
                        with oc4:
                            if st.button("🔗 Share", key=f"share_{w['id']}", use_container_width=True):
                                share_result = post(f"/api/workspaces/{w['id']}/share")
                                st.session_state[f"share_token_{w['id']}"] = share_result["share_token"]

                        if st.session_state.get(f"share_token_{w['id']}"):
                            st.code(st.session_state[f"share_token_{w['id']}"], language=None)
                            st.caption("Share this token — others can redeem it below under 'Join a Shared Workspace' to get full access.")

                        if st.session_state.get(f"editing_{w['id']}"):
                            with st.form(f"edit_form_{w['id']}"):
                                e_name = st.text_input("Name", value=w["name"])
                                e_desc = st.text_area("Description", value=w.get("description", ""))
                                e_prompt = st.text_area("Workspace Prompt", value=w.get("workspace_prompt", ""))
                                ec1, ec2 = st.columns(2)
                                with ec1:
                                    if st.form_submit_button("Save Changes", use_container_width=True):
                                        patch(f"/api/workspaces/{w['id']}",
                                              json={"name": e_name, "description": e_desc, "workspace_prompt": e_prompt})
                                        del st.session_state[f"editing_{w['id']}"]
                                        st.rerun()
                                with ec2:
                                    if st.form_submit_button("Cancel", use_container_width=True):
                                        del st.session_state[f"editing_{w['id']}"]
                                        st.rerun()

                        if st.button("🗑️ Delete Workspace", key=f"del_{w['id']}", use_container_width=True):
                            st.session_state[f"confirm_del_{w['id']}"] = True

                    if st.session_state.get(f"confirm_del_{w['id']}"):
                        st.warning(f"Delete **{w['name']}** permanently? This removes all its chats, documents, and memory.")
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("Yes, delete it", key=f"confirm_yes_{w['id']}", use_container_width=True):
                                delete(f"/api/workspaces/{w['id']}")
                                del st.session_state[f"confirm_del_{w['id']}"]
                                st.rerun()
                        with cc2:
                            if st.button("Cancel", key=f"confirm_no_{w['id']}", use_container_width=True):
                                del st.session_state[f"confirm_del_{w['id']}"]
                                st.rerun()
        else:
            empty_state("🗂️", "No workspaces yet", "Create your first workspace to get started")

    with col2:
        st.markdown("#### Create Workspace")
        with st.container(border=True):
            with st.form("new_workspace"):
                new_name = st.text_input("Name", placeholder="Research Team")
                new_desc = st.text_area("Description", height=70, placeholder="What is this workspace for?")
                new_prompt = st.text_area("Workspace Prompt (optional)", height=70)
                if st.form_submit_button("＋ Create Workspace", use_container_width=True):
                    post("/api/workspaces", json={"name": new_name, "description": new_desc,
                                                   "workspace_prompt": new_prompt})
                    st.rerun()

        gradient_divider()
        st.markdown("#### Join a Shared Workspace")
        with st.container(border=True):
            with st.form("join_workspace"):
                token_input = st.text_input("Share Token", placeholder="Paste a share token here")
                if st.form_submit_button("Join Workspace", use_container_width=True):
                    try:
                        joined = post(f"/api/workspaces/join/{token_input}")
                        st.success(f"Joined '{joined['name']}'!")
                        st.rerun()
                    except requests.HTTPError:
                        st.error("Invalid or expired share token.")
