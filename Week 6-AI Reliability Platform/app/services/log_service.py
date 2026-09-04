"""Observability helper — writes a Log row for every notable event."""
from app.models.models import db, Log


def log_event(event_type, message="", user_id=None, workspace_id=None,
              input_tokens=0, output_tokens=0, latency_ms=0):
    entry = Log(
        event_type=event_type,
        message=message[:500],
        user_id=user_id,
        workspace_id=workspace_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )
    db.session.add(entry)
    db.session.commit()
    return entry
