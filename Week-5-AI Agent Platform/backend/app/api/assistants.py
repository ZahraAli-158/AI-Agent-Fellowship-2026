from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.workspaces import _get_owned_workspace
from app.core.config import get_settings
from app.db.session import get_db
from app.models.assistant import Assistant
from app.models.user import User
from app.schemas.core import AssistantCreate, AssistantOut

router = APIRouter(prefix="/api/workspaces/{workspace_id}/assistants", tags=["assistants"])


@router.post("", response_model=AssistantOut, status_code=201)
def create_assistant(workspace_id: str, payload: AssistantCreate, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    settings = get_settings()
    data = payload.model_dump()
    # Root-cause fix applied here too: explicit None model -> DEFAULT_MODEL,
    # never a hardcoded "mock-gpt".
    data["model"] = data["model"] or settings.DEFAULT_MODEL
    assistant = Assistant(workspace_id=workspace_id, **data)
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return assistant


@router.get("", response_model=list[AssistantOut])
def list_assistants(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    return db.query(Assistant).filter(Assistant.workspace_id == workspace_id).all()


@router.get("/{assistant_id}", response_model=AssistantOut)
def get_assistant(workspace_id: str, assistant_id: str, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    assistant = db.get(Assistant, assistant_id)
    if not assistant or assistant.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Assistant not found")
    return assistant
