"""
Long-term memory service.

Memory persists at the workspace level (independent of any single
conversation/session) and is re-injected into the system prompt on every
chat turn, so the assistant "remembers" preferences, prior discussions,
frequently asked topics, and pinned information across sessions.
"""
import re
from datetime import datetime

from app.models.models import db, MemoryItem

PREFERENCE_PATTERNS = [
    r"\bi (?:like|love|prefer|enjoy)\b (.+)",
    r"\bi (?:hate|dislike|don't like)\b (.+)",
    r"\bmy name is\b (.+)",
    r"\bcall me\b (.+)",
    r"\bremember that\b (.+)",
    r"\bplease remember\b (.+)",
    r"\bi am\b (?:a|an) (.+)",
    r"\bi work\b (?:as|at|on) (.+)",
]


def extract_candidate_memories(user_message: str):
    """Very lightweight rule-based extraction of memorable statements from a
    user message. Returns list[str] of candidate facts to store."""
    found = []
    lowered = user_message.lower()
    for pattern in PREFERENCE_PATTERNS:
        match = re.search(pattern, lowered)
        if match:
            found.append(user_message.strip())
            break
    return found


def store_memory(workspace_id, content, category="preference"):
    existing = MemoryItem.query.filter_by(workspace_id=workspace_id, content=content).first()
    if existing:
        existing.weight += 1
        existing.last_used_at = datetime.utcnow()
        db.session.commit()
        return existing

    item = MemoryItem(workspace_id=workspace_id, content=content, category=category)
    db.session.add(item)
    db.session.commit()
    return item


def track_topic(workspace_id, topic: str):
    """Increment weight of a frequently-asked topic, or create it."""
    existing = MemoryItem.query.filter_by(
        workspace_id=workspace_id, category="topic", content=topic
    ).first()
    if existing:
        existing.weight += 1
        existing.last_used_at = datetime.utcnow()
    else:
        existing = MemoryItem(workspace_id=workspace_id, category="topic", content=topic)
        db.session.add(existing)
    db.session.commit()
    return existing


def get_relevant_memory_context(workspace_id, limit=8):
    """Builds a compact text block of the most relevant memory items
    (pinned first, then by weight/recency) to inject into the system prompt."""
    pinned = MemoryItem.query.filter_by(workspace_id=workspace_id, is_pinned=True).all()
    others = (
        MemoryItem.query.filter_by(workspace_id=workspace_id, is_pinned=False)
        .order_by(MemoryItem.weight.desc(), MemoryItem.last_used_at.desc())
        .limit(limit)
        .all()
    )

    items = pinned + [o for o in others if o not in pinned]
    if not items:
        return ""

    lines = ["Known long-term memory about this user/workspace (use if relevant, don't repeat verbatim unless asked):"]
    for item in items[:limit]:
        tag = "[PINNED]" if item.is_pinned else f"[{item.category}]"
        lines.append(f"- {tag} {item.content}")
    return "\n".join(lines)
