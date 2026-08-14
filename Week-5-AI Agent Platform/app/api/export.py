"""Advanced Feature: Conversation Export (Markdown + PDF)."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.workspaces import _get_owned_workspace
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.user import User

router = APIRouter(prefix="/api/workspaces/{workspace_id}/conversations/{conversation_id}/export", tags=["export"])


def _get_conversation(workspace_id: str, conversation_id: str, db: Session, user: User) -> Conversation:
    _get_owned_workspace(workspace_id, db, user)
    convo = db.get(Conversation, conversation_id)
    if not convo or convo.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


def _to_markdown(convo: Conversation) -> str:
    lines = [f"# {convo.title}", ""]
    for m in convo.messages:
        speaker = "**User**" if m.role == "user" else "**Assistant**"
        lines.append(f"{speaker} ({m.created_at.isoformat()}):\n\n{m.content}\n")
    return "\n".join(lines)


@router.get("/markdown")
def export_markdown(workspace_id: str, conversation_id: str, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    convo = _get_conversation(workspace_id, conversation_id, db, user)
    return PlainTextResponse(_to_markdown(convo), media_type="text/markdown")


@router.get("/pdf")
def export_pdf(workspace_id: str, conversation_id: str, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    convo = _get_conversation(workspace_id, conversation_id, db, user)

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [Paragraph(convo.title, styles["Title"]), Spacer(1, 0.2 * inch)]
    for m in convo.messages:
        speaker = "User" if m.role == "user" else "Assistant"
        story.append(Paragraph(f"<b>{speaker}:</b> {m.content}", styles["Normal"]))
        story.append(Spacer(1, 0.15 * inch))
    doc.build(story)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf",
                              headers={"Content-Disposition": f"attachment; filename={convo.id}.pdf"})
