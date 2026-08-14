from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.workspaces import _get_owned_workspace
from app.db.session import get_db
from app.models.prompt_template import PromptTemplate
from app.models.user import User
from app.schemas.extras import PromptCreate, PromptOut

router = APIRouter(prefix="/api/workspaces/{workspace_id}/prompts", tags=["prompts"])


@router.post("", response_model=PromptOut, status_code=201)
def create_prompt(workspace_id: str, payload: PromptCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    item = PromptTemplate(workspace_id=workspace_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[PromptOut])
def list_prompts(workspace_id: str, category: str = "", favorites_only: bool = False,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    q = db.query(PromptTemplate).filter(PromptTemplate.workspace_id == workspace_id)
    if category:
        q = q.filter(PromptTemplate.category == category)
    if favorites_only:
        q = q.filter(PromptTemplate.favorite.is_(True))
    return q.order_by(PromptTemplate.created_at.desc()).all()


@router.put("/{prompt_id}", response_model=PromptOut)
def update_prompt(workspace_id: str, prompt_id: str, payload: PromptCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    item = db.get(PromptTemplate, prompt_id)
    if not item or item.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Prompt not found")
    for k, v in payload.model_dump().items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{prompt_id}/duplicate", response_model=PromptOut, status_code=201)
def duplicate_prompt(workspace_id: str, prompt_id: str, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    src = db.get(PromptTemplate, prompt_id)
    if not src or src.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Prompt not found")
    copy = PromptTemplate(
        workspace_id=workspace_id, title=f"{src.title} (Copy)", category=src.category, content=src.content,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy


@router.patch("/{prompt_id}/favorite", response_model=PromptOut)
def toggle_favorite(workspace_id: str, prompt_id: str, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    item = db.get(PromptTemplate, prompt_id)
    if not item or item.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Prompt not found")
    item.favorite = not item.favorite
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{prompt_id}", status_code=204)
def delete_prompt(workspace_id: str, prompt_id: str, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    item = db.get(PromptTemplate, prompt_id)
    if not item or item.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Prompt not found")
    db.delete(item)
    db.commit()
