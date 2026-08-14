from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.workspaces import _get_owned_workspace
from app.core.config import get_settings
from app.db.session import get_db
from app.models.skill import SkillRun
from app.models.user import User
from app.schemas.extras import SkillRunOut, SkillRunRequest
from app.services.llm.factory import get_provider
from app.skills.registry import get_skill_prompt, list_skills

router = APIRouter(prefix="/api/workspaces/{workspace_id}/skills", tags=["skills"])


@router.get("")
def get_available_skills():
    return {"skills": list_skills()}


@router.post("/{skill_name}/run", response_model=SkillRunOut)
def run_skill(workspace_id: str, skill_name: str, payload: SkillRunRequest, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    try:
        system_prompt, user_prompt = get_skill_prompt(skill_name, payload.input_text, payload.extra)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    provider = get_provider(model=get_settings().DEFAULT_MODEL)
    result = provider.generate(messages=[{"role": "user", "content": user_prompt}], system_prompt=system_prompt)

    db.add(SkillRun(workspace_id=workspace_id, skill_name=skill_name,
                     input_summary=payload.input_text[:300], output=result.text))
    db.commit()

    return SkillRunOut(skill_name=skill_name, output=result.text)
