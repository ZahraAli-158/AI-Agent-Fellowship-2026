from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.assistant import Assistant
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.memory import MemoryItem
from app.models.message import Message
from app.models.prompt_template import PromptTemplate
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.schemas.core import WorkspaceCreate, WorkspaceOut

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


def _get_owned_workspace(workspace_id: str, db: Session, user: User) -> Workspace:
    """Resolve a workspace the current user may access: either the owner,
    or a member who joined via a share link. Members get equal read/write
    access for simplicity (documented as a scoping decision in the audit
    report -- role-based permission tiers are a reasonable future
    enhancement, not required by the assignment)."""
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws.owner_id == user.id:
        return ws
    is_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id
    ).first()
    if is_member:
        return ws
    raise HTTPException(status_code=404, detail="Workspace not found")


@router.post("", response_model=WorkspaceOut, status_code=201)
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    ws = Workspace(owner_id=user.id, **payload.model_dump())
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(include_archived: bool = False, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    owned = db.query(Workspace).filter(Workspace.owner_id == user.id)
    member_ids = [m.workspace_id for m in db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).all()]
    shared = db.query(Workspace).filter(Workspace.id.in_(member_ids)) if member_ids else None

    results = list(owned.all())
    if shared is not None:
        results += [w for w in shared.all() if w.id not in {r.id for r in results}]

    if not include_archived:
        results = [w for w in results if not w.archived]
    return results


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _get_owned_workspace(workspace_id, db, user)


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def update_workspace(workspace_id: str, payload: WorkspaceCreate, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """Edit Workspace: name, description, workspace_prompt."""
    ws = _get_owned_workspace(workspace_id, db, user)
    ws.name = payload.name
    ws.description = payload.description
    ws.workspace_prompt = payload.workspace_prompt
    db.commit()
    db.refresh(ws)
    return ws


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ws = db.get(Workspace, workspace_id)
    if not ws or ws.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    db.delete(ws)
    db.commit()


@router.patch("/{workspace_id}/archive", response_model=WorkspaceOut)
def toggle_archive(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Archive/Unarchive Workspace."""
    ws = _get_owned_workspace(workspace_id, db, user)
    ws.archived = not ws.archived
    db.commit()
    db.refresh(ws)
    return ws


@router.post("/{workspace_id}/clone", response_model=WorkspaceOut, status_code=201)
def clone_workspace(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Clone Workspace: copies name/description/prompt plus its assistants
    and prompt templates into a brand-new workspace owned by the caller.
    Conversations, documents, and memory are intentionally NOT copied,
    since a clone is meant as a fresh starting point, not a full duplicate
    of chat history."""
    src = _get_owned_workspace(workspace_id, db, user)

    clone = Workspace(
        owner_id=user.id,
        name=f"{src.name} (Copy)",
        description=src.description,
        workspace_prompt=src.workspace_prompt,
    )
    db.add(clone)
    db.flush()

    for a in db.query(Assistant).filter(Assistant.workspace_id == workspace_id).all():
        db.add(Assistant(
            workspace_id=clone.id, name=a.name, role=a.role, system_prompt=a.system_prompt,
            model=a.model, temperature=a.temperature, max_tokens=a.max_tokens,
            personality=a.personality, response_style=a.response_style,
        ))

    for p in db.query(PromptTemplate).filter(PromptTemplate.workspace_id == workspace_id).all():
        db.add(PromptTemplate(workspace_id=clone.id, title=p.title, category=p.category, content=p.content))

    db.commit()
    db.refresh(clone)
    return clone


@router.post("/{workspace_id}/share")
def create_share_link(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Workspace Sharing: generate (or return existing) a share token that
    anyone with an account can redeem via /join/{token} to become a member
    with full access to this workspace."""
    ws = db.get(Workspace, workspace_id)
    if not ws or ws.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not ws.share_token:
        ws.share_token = str(uuid.uuid4())
        db.commit()
        db.refresh(ws)
    return {"share_token": ws.share_token}


@router.post("/join/{token}", response_model=WorkspaceOut)
def join_workspace(token: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Redeem a share token to join someone else's workspace as a member."""
    ws = db.query(Workspace).filter(Workspace.share_token == token).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Invalid or expired share link")
    if ws.owner_id == user.id:
        return ws
    existing = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws.id, WorkspaceMember.user_id == user.id
    ).first()
    if not existing:
        db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id))
        db.commit()
    return ws


@router.get("/{workspace_id}/stats")
def workspace_stats(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Workspace Statistics: lightweight counts for workspace cards/listing,
    independent of the fuller analytics in the Dashboard endpoint."""
    ws = _get_owned_workspace(workspace_id, db, user)
    conv_count = db.query(func.count(Conversation.id)).filter(Conversation.workspace_id == ws.id).scalar()
    doc_count = db.query(func.count(Document.id)).filter(Document.workspace_id == ws.id).scalar()
    mem_count = db.query(func.count(MemoryItem.id)).filter(MemoryItem.workspace_id == ws.id).scalar()
    msg_count = (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.workspace_id == ws.id)
        .scalar()
    )
    member_count = db.query(func.count(WorkspaceMember.id)).filter(WorkspaceMember.workspace_id == ws.id).scalar()
    return {
        "conversations": conv_count or 0,
        "documents": doc_count or 0,
        "memory_items": mem_count or 0,
        "messages": msg_count or 0,
        "members": (member_count or 0) + 1,  # +1 for the owner
        "archived": ws.archived,
        "is_shared": ws.share_token is not None,
    }
