from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.workspaces import _get_owned_workspace
from app.db.session import get_db
from app.models.assistant import Assistant
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.core import (ChatRequest, ChatResponse, ConversationCreate,
                               ConversationOut, MessageOut)
from app.services.chat_service import run_chat_turn

router = APIRouter(prefix="/api/workspaces/{workspace_id}/conversations", tags=["conversations"])


def _get_conversation(workspace_id: str, conversation_id: str, db: Session, user: User) -> Conversation:
    _get_owned_workspace(workspace_id, db, user)
    convo = db.get(Conversation, conversation_id)
    if not convo or convo.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


@router.post("", response_model=ConversationOut, status_code=201)
def create_conversation(workspace_id: str, payload: ConversationCreate, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    assistant = db.get(Assistant, payload.assistant_id)
    if not assistant or assistant.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Assistant not found in this workspace")
    convo = Conversation(workspace_id=workspace_id, assistant_id=payload.assistant_id, title=payload.title)
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@router.get("", response_model=list[ConversationOut])
def list_conversations(workspace_id: str, search: str = "", db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    q = db.query(Conversation).filter(Conversation.workspace_id == workspace_id)
    if search:
        q = q.filter(Conversation.title.ilike(f"%{search}%"))
    return q.order_by(Conversation.updated_at.desc()).all()


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(workspace_id: str, conversation_id: str, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    convo = _get_conversation(workspace_id, conversation_id, db, user)
    return convo.messages


@router.patch("/{conversation_id}/messages/{message_id}/pin", response_model=MessageOut)
def toggle_message_pin(workspace_id: str, conversation_id: str, message_id: str, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """Pinned Messages / Bookmarks: mark an individual message as pinned so
    it can be surfaced separately from the full conversation history."""
    _get_conversation(workspace_id, conversation_id, db, user)
    msg = db.get(Message, message_id)
    if not msg or msg.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.pinned = not msg.pinned
    db.commit()
    db.refresh(msg)
    return msg


@router.get("/messages/pinned", response_model=list[MessageOut])
def list_pinned_messages(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """All pinned/bookmarked messages across every conversation in this workspace."""
    _get_owned_workspace(workspace_id, db, user)
    return (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.workspace_id == workspace_id, Message.pinned.is_(True))
        .order_by(Message.created_at.desc())
        .all()
    )


@router.patch("/{conversation_id}/rename", response_model=ConversationOut)
def rename_conversation(workspace_id: str, conversation_id: str, title: str, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    convo = _get_conversation(workspace_id, conversation_id, db, user)
    convo.title = title
    db.commit()
    db.refresh(convo)
    return convo


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(workspace_id: str, conversation_id: str, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    convo = _get_conversation(workspace_id, conversation_id, db, user)
    db.delete(convo)
    db.commit()


@router.post("/{conversation_id}/chat", response_model=ChatResponse)
def chat(workspace_id: str, conversation_id: str, payload: ChatRequest, db: Session = Depends(get_db),
         user: User = Depends(get_current_user)):
    convo = _get_conversation(workspace_id, conversation_id, db, user)
    assistant = db.get(Assistant, convo.assistant_id)
    user_msg, assistant_msg = run_chat_turn(db, convo, assistant, payload.message)
    if convo.title == "New Conversation":
        convo.title = payload.message[:60]
        db.commit()
    return ChatResponse(conversation_id=convo.id, user_message=user_msg, assistant_message=assistant_msg)
