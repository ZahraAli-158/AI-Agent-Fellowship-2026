from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _default_model() -> str:
    # Root-cause fix: new assistants must inherit DEFAULT_MODEL from Settings,
    # never a hardcoded literal like "mock-gpt".
    return get_settings().DEFAULT_MODEL


class Assistant(Base):
    __tablename__ = "assistants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), default="General Assistant")
    system_prompt: Mapped[str] = mapped_column(Text, default="You are a helpful assistant.")
    model: Mapped[str] = mapped_column(String(100), default=_default_model)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=1024)
    personality: Mapped[str] = mapped_column(String(255), default="neutral")
    response_style: Mapped[str] = mapped_column(String(255), default="concise")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="assistants")
    conversations = relationship("Conversation", back_populates="assistant")
