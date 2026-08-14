import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import get
from components import empty_state, gradient_divider, metric_glow, page_header
from nav import require_workspace
from theme import ACCENT, ACCENT_2, BG_SECONDARY, BORDER, TEXT_SECONDARY

require_workspace()
ws_id = st.session_state.workspace_id

page_header("🏠", "Dashboard", f"Overview & analytics for {st.session_state.workspace_name}")
gradient_divider()

data = get(f"/api/workspaces/{ws_id}/dashboard")

# --- Top metric row ---
c1, c2, c3, c4, c5 = st.columns(5)
with c1: metric_glow("Conversations", str(data["conversations"]), "purple")
with c2: metric_glow("Documents", str(data["documents"]), "blue")
with c3: metric_glow("Memory Items", str(data["memory_items"]), "green")
with c4: metric_glow("Prompt Templates", str(data["prompt_templates"]), "yellow")
with c5: metric_glow("Est. Cost", f"${data['estimated_cost_usd']:.4f}", "red")

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

c6, c7, c8 = st.columns(3)
with c6: metric_glow("Input Tokens", f"{data['total_input_tokens']:,}", "blue")
with c7: metric_glow("Output Tokens", f"{data['total_output_tokens']:,}", "purple")
with c8: metric_glow("Active Model", data["active_model"], "green")

gradient_divider()

# --- Quick Actions ---
st.markdown("#### Quick Actions")
qa1, qa2, qa3, qa4 = st.columns(4)
with qa1:
    if st.button("💬 Start Chat", use_container_width=True):
        st.switch_page("pages/2_Chat.py")
with qa2:
    if st.button("📄 Upload Document", use_container_width=True):
        st.switch_page("pages/3_Knowledge_Base.py")
with qa3:
    if st.button("📝 Create Prompt", use_container_width=True):
        st.switch_page("pages/5_Prompt_Library.py")
with qa4:
    if st.button("🤖 Configure Assistant", use_container_width=True):
        st.switch_page("pages/7_Assistant_Settings.py")

gradient_divider()

# --- Charts (Analytics) ---
st.markdown("#### Analytics")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown("<div class='awp-muted' style='margin-bottom:6px;'>Token Usage</div>", unsafe_allow_html=True)
    fig = go.Figure(data=[
        go.Bar(name="Input", x=["Tokens"], y=[data["total_input_tokens"]], marker_color=ACCENT),
        go.Bar(name="Output", x=["Tokens"], y=[data["total_output_tokens"]], marker_color=ACCENT_2),
    ])
    fig.update_layout(
        barmode="group", height=260, plot_bgcolor=BG_SECONDARY, paper_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT_SECONDARY, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", y=1.15),
    )
    st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    st.markdown("<div class='awp-muted' style='margin-bottom:6px;'>Workspace Composition</div>", unsafe_allow_html=True)
    labels = ["Conversations", "Documents", "Memory", "Prompts"]
    values = [data["conversations"], data["documents"], data["memory_items"], data["prompt_templates"]]
    fig2 = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.6,
        marker=dict(colors=[ACCENT, ACCENT_2, "#3B82F6", "#EAB308"]),
    )])
    fig2.update_layout(
        height=260, paper_bgcolor="rgba(0,0,0,0)", font_color=TEXT_SECONDARY,
        margin=dict(l=10, r=10, t=10, b=10), showlegend=True,
        legend=dict(orientation="h", y=-0.1),
    )
    st.plotly_chart(fig2, use_container_width=True)

gradient_divider()

st.markdown("#### Recent Activity")
if data["recent_activity"]:
    for item in data["recent_activity"][:8]:
        icon = "🧑" if item["role"] == "user" else "🤖"
        with st.container(border=True):
            st.markdown(f"{icon} **{item['role'].title()}** · <span class='awp-muted' style='font-size:12px'>{item['created_at'][:19].replace('T',' ')}</span>", unsafe_allow_html=True)
            st.markdown(f"<span class='awp-muted'>{item['content']}</span>", unsafe_allow_html=True)
else:
    empty_state("📊", "No activity yet", "Start a conversation to see activity here")
