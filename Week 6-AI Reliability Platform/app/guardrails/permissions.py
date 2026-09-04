"""
Tool security / risk classification (Week 6, Requirement 15).

Every tool the platform exposes (Meeting Agent tools, future agents' tools)
is classified into a risk level. L3+ requires human approval before it is
allowed to execute — enforced here, not left to the LLM's judgement.
"""

RISK_LEVELS = {
    "L0": "informational",  # e.g. search, list, read-only lookups with no side effects
    "L1": "read",            # reads user-owned data
    "L2": "write",           # creates/updates user-owned data
    "L3": "sensitive",       # sends data outside the system (email), reads cross-user data
    "L4": "destructive",     # deletes data, irreversible actions
}

# Tool registry: tool_name -> risk level. Extend as new tools are added.
TOOL_RISK = {
    "create_task": "L2",
    "list_tasks": "L1",
    "update_task": "L2",
    "complete_task": "L2",
    "delete_task": "L4",
    "search_tasks": "L0",
    "email_task_summary": "L3",
    "search_knowledge_base": "L0",
    "read_document": "L1",
}

APPROVAL_REQUIRED_LEVELS = {"L3", "L4"}


class PermissionDenied(Exception):
    pass


def risk_level_of(tool_name: str) -> str:
    return TOOL_RISK.get(tool_name, "L3")  # unknown tools default to "sensitive": safest default


def requires_approval(tool_name: str) -> bool:
    return risk_level_of(tool_name) in APPROVAL_REQUIRED_LEVELS


def authorize_tool_call(tool_name: str, approved: bool = False):
    """Raises PermissionDenied unless the call is allowed.

    A high-risk tool call must never execute merely because the LLM decided
    to call it — this function is the single choke point every tool
    invocation must pass through before it runs."""
    level = risk_level_of(tool_name)
    if level in APPROVAL_REQUIRED_LEVELS and not approved:
        raise PermissionDenied(
            f"Tool '{tool_name}' is risk level {level} ({RISK_LEVELS[level]}) and requires "
            f"explicit human approval before it can execute."
        )
    return True
