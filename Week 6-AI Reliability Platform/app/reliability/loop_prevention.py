"""
Agent loop prevention (Week 6, Requirement 19).

Bounds an agent's execution so a confused model can't loop forever or spam
the same tool call. Raise LoopLimitExceeded to produce a controlled failure
instead of a hang / runaway cost.
"""

DEFAULT_MAX_STEPS = 12
DEFAULT_MAX_TOOL_CALLS = 8
DEFAULT_MAX_REVISIONS = 3


class LoopLimitExceeded(Exception):
    pass


class AgentLoopGuard:
    """Bounds a single agent turn's execution. `max_revisions` /
    `record_revision()` are provided as general-purpose infrastructure for
    any future workflow that includes a self-critique/revise cycle (as the
    separate Week 4 MADIP multi-agent project does); the current
    single-turn Meeting Agent (app/services/agent_service.py) has no
    revision loop of its own, so record_revision() is never called there —
    see docs/WEEK6_AGENT_EVALUATION.md for the same honest scoping applied
    to multi-agent metrics."""

    def __init__(self, max_steps=DEFAULT_MAX_STEPS, max_tool_calls=DEFAULT_MAX_TOOL_CALLS,
                 max_revisions=DEFAULT_MAX_REVISIONS):
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.max_revisions = max_revisions
        self.steps = 0
        self.tool_calls = 0
        self.revisions = 0
        self._seen_actions = set()

    def record_step(self):
        self.steps += 1
        if self.steps > self.max_steps:
            raise LoopLimitExceeded(f"Exceeded max agent steps ({self.max_steps})")

    def record_tool_call(self, tool_name, args_signature):
        self.tool_calls += 1
        if self.tool_calls > self.max_tool_calls:
            raise LoopLimitExceeded(f"Exceeded max tool calls ({self.max_tool_calls})")
        key = (tool_name, args_signature)
        if key in self._seen_actions:
            raise LoopLimitExceeded(f"Duplicate action detected: {tool_name}({args_signature})")
        self._seen_actions.add(key)

    def record_revision(self):
        self.revisions += 1
        if self.revisions > self.max_revisions:
            raise LoopLimitExceeded(f"Exceeded max revision cycles ({self.max_revisions})")
