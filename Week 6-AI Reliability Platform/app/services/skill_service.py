"""
AI Skills: reusable, single-purpose prompt-driven capabilities usable from
any workspace (Module 8). Each skill is a (key, name, description, icon,
prompt_template) tuple seeded into the `skills` table on first run.
`{input}` in the template is replaced with the user-provided text.
"""
from app.models.models import db, Skill

DEFAULT_SKILLS = [
    dict(
        key="research",
        name="Research Skill",
        description="Investigate a topic and produce a structured briefing with key findings.",
        icon="\U0001F50D",
        prompt_template=(
            "Act as a research analyst. Research and explain the following topic. "
            "Structure your answer with: Overview, Key Points (bulleted), and "
            "Open Questions. Be factual and note any uncertainty.\n\nTopic:\n{input}"
        ),
    ),
    dict(
        key="summarization",
        name="Summarization Skill",
        description="Condense long text into a clear, faithful summary.",
        icon="\U0001F4DD",
        prompt_template=(
            "Summarize the following text. Preserve the key facts and intent, "
            "remove redundancy, and keep it under 150 words unless the text is "
            "very long.\n\nText:\n{input}"
        ),
    ),
    dict(
        key="email",
        name="Email Skill",
        description="Draft a clear, professional email from a short brief.",
        icon="\U0001F4E7",
        prompt_template=(
            "Write a professional email based on this brief. Include a subject "
            "line, greeting, body, and sign-off. Keep tone professional and "
            "concise.\n\nBrief:\n{input}"
        ),
    ),
    dict(
        key="report",
        name="Report Generator",
        description="Turn notes or data into a structured report with sections.",
        icon="\U0001F4C4",
        prompt_template=(
            "Generate a structured report from the following notes. Include: "
            "Title, Executive Summary, Findings, Recommendations, and "
            "Conclusion.\n\nNotes:\n{input}"
        ),
    ),
    dict(
        key="meeting_notes",
        name="Meeting Notes Extractor",
        description="Extract decisions, action items, and owners from meeting notes.",
        icon="\U0001F5D3\uFE0F",
        prompt_template=(
            "From the following raw meeting notes/transcript, extract: "
            "1) Key Discussion Points, 2) Decisions Made, 3) Action Items "
            "(with owner and due date if mentioned). Use bullet points.\n\n"
            "Notes:\n{input}"
        ),
    ),
    dict(
        key="idea_generator",
        name="Idea Generator",
        description="Brainstorm creative, varied ideas around a prompt or problem.",
        icon="\U0001F4A1",
        prompt_template=(
            "Brainstorm 8 diverse, creative ideas related to the following prompt. "
            "Number them, keep each to 1-2 sentences, and cover different angles "
            "(not just variations of the same idea).\n\nPrompt:\n{input}"
        ),
    ),
    dict(
        key="task_planner",
        name="Task Planner",
        description="Break a goal down into an ordered, actionable task list.",
        icon="\u2705",
        prompt_template=(
            "Break the following goal down into an ordered, actionable task "
            "list with realistic milestones. Use a numbered list, group into "
            "phases if useful.\n\nGoal:\n{input}"
        ),
    ),
    dict(
        key="swot",
        name="SWOT Generator",
        description="Produce a Strengths/Weaknesses/Opportunities/Threats analysis.",
        icon="\U0001F4CA",
        prompt_template=(
            "Produce a SWOT analysis (Strengths, Weaknesses, Opportunities, "
            "Threats) for the following subject. Use 3-5 bullets per "
            "quadrant.\n\nSubject:\n{input}"
        ),
    ),
    dict(
        key="business_canvas",
        name="Business Canvas Generator",
        description="Draft a Lean/Business Model Canvas from a business idea.",
        icon="\U0001F9E9",
        prompt_template=(
            "Draft a Business Model Canvas for the following idea. Cover: "
            "Value Proposition, Customer Segments, Channels, Revenue Streams, "
            "Key Resources, Key Activities, Key Partners, Cost Structure, and "
            "Customer Relationships.\n\nIdea:\n{input}"
        ),
    ),
    dict(
        key="code_reviewer",
        name="Code Reviewer",
        description="Review code for bugs, style, and improvement opportunities.",
        icon="\U0001F9D1\u200D\U0001F4BB",
        prompt_template=(
            "Review the following code. Report: 1) Bugs/correctness issues, "
            "2) Style/readability issues, 3) Performance or security concerns, "
            "4) Suggested improvements with brief code snippets where useful.\n\n"
            "Code:\n{input}"
        ),
    ),
]


def seed_skills():
    """Idempotently ensure the default skill set exists in the database."""
    for s in DEFAULT_SKILLS:
        if not Skill.query.filter_by(key=s["key"]).first():
            db.session.add(Skill(**s))
    db.session.commit()


def build_skill_prompt(skill: Skill, user_input: str) -> str:
    return skill.prompt_template.format(input=user_input)
