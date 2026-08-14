from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# --- Auth ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Workspace ---
class WorkspaceCreate(BaseModel):
    name: str
    description: str = ""
    workspace_prompt: str = ""


class WorkspaceOut(BaseModel):
    id: str
    name: str
    description: str
    workspace_prompt: str
    archived: bool = False
    share_token: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Assistant ---
class AssistantCreate(BaseModel):
    name: str
    role: str = "General Assistant"
    system_prompt: str = "You are a helpful assistant."
    model: Optional[str] = None  # None -> DEFAULT_MODEL
    temperature: float = 0.7
    max_tokens: int = 1024
    personality: str = "neutral"
    response_style: str = "concise"


class AssistantOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    role: str
    system_prompt: str
    model: str
    temperature: float
    max_tokens: int
    personality: str
    response_style: str
    created_at: datetime

    class Config:
        from_attributes = True
        protected_namespaces = ()


# --- Conversation / Chat ---
class ConversationCreate(BaseModel):
    assistant_id: str
    title: str = "New Conversation"


class ConversationOut(BaseModel):
    id: str
    workspace_id: str
    assistant_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    model_used: str
    provider_used: str
    input_tokens: int
    output_tokens: int
    response_time_ms: int = 0
    pinned: bool = False
    created_at: datetime

    class Config:
        from_attributes = True
        protected_namespaces = ()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    conversation_id: str
    user_message: MessageOut
    assistant_message: MessageOut
