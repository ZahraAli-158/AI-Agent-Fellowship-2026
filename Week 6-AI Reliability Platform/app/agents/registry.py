"""
Agent registry — a small catalog of specialized agents, completely separate
from Workspaces. Unlike a Workspace assistant (a configurable prompt), each
agent here has a fixed identity AND a fixed set of real tools it can call
via Gemini function-calling (see app/services/agent_service.py for the
tool implementations and the call loop).

To add a new agent: add an entry here (key, name, icon, description,
system_prompt) and add a matching tool-builder in agent_service.py's
TOOL_BUILDERS registry.
"""

AGENTS = {
    "meeting": {
        "key": "meeting",
        "name": "Meeting Agent",
        "icon": "📅",
        "description": (
            "Handles everything meeting-related: extracts decisions and action "
            "items from raw notes, and manages your task list — create, list, "
            "update, complete, delete — then can email you a summary."
        ),
        "system_prompt": (
            "You are the Meeting Agent, a focused productivity assistant. Your job "
            "is to help the user turn meetings into tracked, actionable work.\n\n"
            "You have real tools — use them proactively instead of just describing "
            "what you would do:\n"
            "- extract_meeting_notes: call this whenever the user pastes raw meeting "
            "notes or a transcript. It returns structured decisions and action items.\n"
            "- create_task / list_tasks / update_task / complete_task / delete_task: "
            "use these to actually manage the user's task list. When notes contain "
            "clear action items, create a task for each one rather than just listing "
            "them in your reply.\n"
            "- send_email_summary: use this when the user asks to be emailed their "
            "tasks, a meeting summary, or their work — write a clear, well-formatted "
            "subject and body first.\n\n"
            "Always confirm what you did in plain language after calling tools "
            "(e.g. 'Created 3 tasks from these notes and marked task #4 as "
            "complete.'). Ask a clarifying question only when the request is "
            "genuinely ambiguous — otherwise just act."
        ),
    },
}


def get_agent(agent_key):
    return AGENTS.get(agent_key)


def list_agents():
    return list(AGENTS.values())
