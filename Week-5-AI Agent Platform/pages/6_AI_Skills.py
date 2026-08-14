import streamlit as st

from api_client import get, post
from components import empty_state, gradient_divider, page_header
from nav import require_workspace

require_workspace()
ws_id = st.session_state.workspace_id

page_header("⚡", "AI Skills", "Run reusable, purpose-built AI workflows")
gradient_divider()

SKILL_META = {
    "research": ("🔬", "Produce a structured research brief with key facts and open questions."),
    "summarization": ("📄", "Condense long text into a clear, accurate summary."),
    "email_generator": ("✉️", "Draft a professional email on any topic."),
    "report_generator": ("📊", "Write a structured business or technical report."),
    "meeting_notes": ("🗒️", "Turn raw meeting notes into organized minutes and action items."),
    "task_planner": ("✅", "Break a goal down into an actionable, prioritized plan."),
    "swot_generator": ("🧭", "Generate a SWOT analysis: Strengths, Weaknesses, Opportunities, Threats."),
}

skills = get(f"/api/workspaces/{ws_id}/skills")["skills"]

st.markdown("#### Choose a Skill")
cols = st.columns(3)
if "selected_skill" not in st.session_state:
    st.session_state.selected_skill = skills[0] if skills else None

for i, skill in enumerate(skills):
    icon, desc = SKILL_META.get(skill, ("⚡", "Reusable AI skill."))
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"### {icon}")
            st.markdown(f"**{skill.replace('_', ' ').title()}**")
            st.markdown(f"<span class='awp-muted' style='font-size:13px;'>{desc}</span>", unsafe_allow_html=True)
            if st.button("▶ Run", key=f"select_{skill}", use_container_width=True):
                st.session_state.selected_skill = skill

gradient_divider()

if st.session_state.selected_skill:
    st.markdown(f"#### Run: {st.session_state.selected_skill.replace('_', ' ').title()}")
    with st.container(border=True):
        input_text = st.text_area("Input", height=160,
                                   placeholder="Paste text, describe a task, or provide context…")
        if st.button("⚡ Run Skill", use_container_width=True) and input_text:
            with st.spinner(f"Running '{st.session_state.selected_skill}'…"):
                result = post(f"/api/workspaces/{ws_id}/skills/{st.session_state.selected_skill}/run",
                               json={"input_text": input_text, "extra": {}})
            gradient_divider()
            st.markdown("#### Output")
            st.markdown(result["output"])
else:
    empty_state("⚡", "No skills available", "Skills should appear automatically from the backend")
