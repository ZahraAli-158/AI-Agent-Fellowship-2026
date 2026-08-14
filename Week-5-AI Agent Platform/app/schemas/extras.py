from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MemoryCreate(BaseModel):
    category: str = "general"
    content: str
    pinned: bool = False


class MemoryOut(BaseModel):
    id: str
    category: str
    content: str
    pinned: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PromptCreate(BaseModel):
    title: str
    category: str = "custom"
    content: str


class PromptOut(BaseModel):
    id: str
    title: str
    category: str
    content: str
    favorite: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class SkillRunRequest(BaseModel):
    input_text: str
    extra: dict = {}


class SkillRunOut(BaseModel):
    skill_name: str
    output: str


class DashboardOut(BaseModel):
    conversations: int
    documents: int
    memory_items: int
    prompt_templates: int
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost_usd: float
    active_model: str
    active_provider: str
    recent_activity: list[dict]
