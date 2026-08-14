"""
AI Skills registry.

Each skill is a (name, prompt_builder) pair rather than a separate class/file
per skill -- this avoids the "tiny file with 5 lines" anti-pattern while
still keeping each skill's prompt logic independent and easy to extend.
All skills route through the same LLM provider factory, so they respect
DEFAULT_MODEL / assistant overrides exactly like chat does.
"""
from __future__ import annotations

from typing import Callable

SkillPromptBuilder = Callable[[str, dict], tuple[str, str]]  # -> (system_prompt, user_prompt)


def _research(input_text: str, extra: dict) -> tuple[str, str]:
    return (
        "You are a research assistant. Produce a structured research brief with "
        "key facts, context, and open questions.",
        f"Research topic: {input_text}",
    )


def _summarization(input_text: str, extra: dict) -> tuple[str, str]:
    length = extra.get("length", "short")
    return (
        f"You are a summarization assistant. Produce a {length} summary preserving key facts.",
        f"Summarize:\n\n{input_text}",
    )


def _email_generator(input_text: str, extra: dict) -> tuple[str, str]:
    tone = extra.get("tone", "professional")
    return (
        f"You write clear, {tone} emails.",
        f"Write an email about: {input_text}",
    )


def _report_generator(input_text: str, extra: dict) -> tuple[str, str]:
    return (
        "You write structured business/technical reports with headings and bullet points.",
        f"Write a report on: {input_text}",
    )


def _meeting_notes(input_text: str, extra: dict) -> tuple[str, str]:
    return (
        "You convert raw meeting transcripts/notes into structured minutes: "
        "attendees, discussion points, decisions, action items.",
        f"Raw meeting notes:\n\n{input_text}",
    )


def _task_planner(input_text: str, extra: dict) -> tuple[str, str]:
    return (
        "You break down goals into an actionable, prioritized task plan with estimated effort.",
        f"Goal: {input_text}",
    )


def _swot_generator(input_text: str, extra: dict) -> tuple[str, str]:
    return (
        "You produce a SWOT analysis (Strengths, Weaknesses, Opportunities, Threats) as four "
        "clearly labeled sections.",
        f"Subject for SWOT analysis: {input_text}",
    )


def _business_canvas(input_text: str, extra: dict) -> tuple[str, str]:
    return (
        "You produce a Business Model Canvas with these labeled sections: Key Partners, Key "
        "Activities, Key Resources, Value Propositions, Customer Relationships, Channels, "
        "Customer Segments, Cost Structure, Revenue Streams.",
        f"Business idea: {input_text}",
    )


def _code_review(input_text: str, extra: dict) -> tuple[str, str]:
    return (
        "You are a senior code reviewer. Review the given code for bugs, security issues, "
        "readability, and performance. Structure feedback as: Issues Found, Suggestions, "
        "Overall Assessment.",
        f"Review this code:\n\n{input_text}",
    )


def _idea_generator(input_text: str, extra: dict) -> tuple[str, str]:
    count = extra.get("count", 5)
    return (
        f"You generate {count} distinct, creative ideas on a given topic, each with a one-line "
        "explanation of why it could work.",
        f"Generate ideas about: {input_text}",
    )


SKILLS: dict[str, SkillPromptBuilder] = {
    "research": _research,
    "summarization": _summarization,
    "email_generator": _email_generator,
    "report_generator": _report_generator,
    "meeting_notes": _meeting_notes,
    "task_planner": _task_planner,
    "swot_generator": _swot_generator,
    "business_canvas": _business_canvas,
    "code_review": _code_review,
    "idea_generator": _idea_generator,
}


def list_skills() -> list[str]:
    return sorted(SKILLS.keys())


def get_skill_prompt(skill_name: str, input_text: str, extra: dict) -> tuple[str, str]:
    if skill_name not in SKILLS:
        raise KeyError(f"Unknown skill '{skill_name}'. Available: {list_skills()}")
    return SKILLS[skill_name](input_text, extra)
