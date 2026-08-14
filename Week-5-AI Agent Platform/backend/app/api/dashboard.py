from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.workspaces import _get_owned_workspace
from app.core.config import get_settings
from app.core.model_registry import resolve_provider_name
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.memory import MemoryItem
from app.models.message import Message
from app.models.prompt_template import PromptTemplate
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.extras import DashboardOut

router = APIRouter(prefix="/api/workspaces/{workspace_id}/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def get_dashboard(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    settings = get_settings()

    conv_count = db.query(func.count(Conversation.id)).filter(Conversation.workspace_id == workspace_id).scalar()
    doc_count = db.query(func.count(Document.id)).filter(Document.workspace_id == workspace_id).scalar()
    mem_count = db.query(func.count(MemoryItem.id)).filter(MemoryItem.workspace_id == workspace_id).scalar()
    prompt_count = db.query(func.count(PromptTemplate.id)).filter(PromptTemplate.workspace_id == workspace_id).scalar()

    usage_totals = (
        db.query(func.coalesce(func.sum(UsageLog.input_tokens), 0),
                  func.coalesce(func.sum(UsageLog.output_tokens), 0),
                  func.coalesce(func.sum(UsageLog.estimated_cost_usd), 0.0))
        .filter(UsageLog.workspace_id == workspace_id).first()
    )

    recent_messages = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.workspace_id == workspace_id)
        .order_by(Message.created_at.desc())
        .limit(10)
        .all()
    )
    recent_activity = [
        {"role": m.role, "content": m.content[:120], "created_at": m.created_at.isoformat()}
        for m in recent_messages
    ]

    return DashboardOut(
        conversations=conv_count or 0,
        documents=doc_count or 0,
        memory_items=mem_count or 0,
        prompt_templates=prompt_count or 0,
        total_input_tokens=usage_totals[0] or 0,
        total_output_tokens=usage_totals[1] or 0,
        estimated_cost_usd=round(usage_totals[2] or 0.0, 6),
        active_model=settings.DEFAULT_MODEL,
        active_provider=resolve_provider_name(settings.DEFAULT_MODEL),
        recent_activity=recent_activity,
    )
