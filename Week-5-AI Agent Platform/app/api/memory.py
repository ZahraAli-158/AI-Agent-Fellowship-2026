from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.workspaces import _get_owned_workspace
from app.db.session import get_db
from app.models.memory import MemoryItem
from app.models.user import User
from app.schemas.extras import MemoryCreate, MemoryOut

router = APIRouter(prefix="/api/workspaces/{workspace_id}/memory", tags=["memory"])


@router.post("", response_model=MemoryOut, status_code=201)
def add_memory(workspace_id: str, payload: MemoryCreate, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    item = MemoryItem(workspace_id=workspace_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[MemoryOut])
def list_memory(workspace_id: str, category: str = "", db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    q = db.query(MemoryItem).filter(MemoryItem.workspace_id == workspace_id)
    if category:
        q = q.filter(MemoryItem.category == category)
    return q.order_by(MemoryItem.pinned.desc(), MemoryItem.created_at.desc()).all()


@router.patch("/{memory_id}/pin", response_model=MemoryOut)
def toggle_pin(workspace_id: str, memory_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    item = db.get(MemoryItem, memory_id)
    if not item or item.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Memory item not found")
    item.pinned = not item.pinned
    db.commit()
    db.refresh(item)
    return item


@router.put("/{memory_id}", response_model=MemoryOut)
def update_memory(workspace_id: str, memory_id: str, payload: MemoryCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Edit Memory: update category/content/pinned in place."""
    _get_owned_workspace(workspace_id, db, user)
    item = db.get(MemoryItem, memory_id)
    if not item or item.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Memory item not found")
    item.category = payload.category
    item.content = payload.content
    item.pinned = payload.pinned
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{memory_id}", status_code=204)
def delete_memory(workspace_id: str, memory_id: str, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    item = db.get(MemoryItem, memory_id)
    if not item or item.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Memory item not found")
    db.delete(item)
    db.commit()
