"""Advanced Feature: Voice Input (speech-to-text via OpenAI Whisper)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.workspaces import _get_owned_workspace
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/api/workspaces/{workspace_id}/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe_audio(workspace_id: str, file: UploadFile = File(...), db: Session = Depends(get_db),
                            user: User = Depends(get_current_user)):
    """Accepts a recorded audio clip and transcribes it to text using
    OpenAI's Whisper API. Requires OPENAI_API_KEY to be configured -- if it
    isn't, this returns a clear 400 error rather than silently faking a
    transcription, since there is no offline speech-to-text fallback bundled
    with this project."""
    _get_owned_workspace(workspace_id, db, user)
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="Voice transcription requires OPENAI_API_KEY to be configured (uses OpenAI Whisper).",
        )

    try:
        from openai import OpenAI
    except ImportError:
        raise HTTPException(status_code=500, detail="openai package not installed")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    audio_bytes = await file.read()

    import io
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = file.filename or "audio.wav"

    transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return {"text": transcript.text}
