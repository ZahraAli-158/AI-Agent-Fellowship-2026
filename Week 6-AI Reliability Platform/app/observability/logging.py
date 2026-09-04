"""
Structured logging (Week 6, Requirement 8).

Emits single-line JSON log records for the lifecycle events the spec asks
for, in addition to (not instead of) the existing Log/log_event() DB rows
used by the Week 1-5 usage dashboard. Structured logs go to the standard
Python logger "ai_platform.events" so they can be piped to a file, stdout,
or a log aggregator without touching application code.
"""
import json
import logging
import time

logger = logging.getLogger("ai_platform.events")

EVENT_TYPES = {
    "request_received", "model_called", "retrieval_started", "retrieval_completed",
    "tool_selected", "tool_succeeded", "tool_failed", "retry_attempted",
    "guardrail_triggered", "evaluation_completed", "request_completed",
}


def log_structured(event, **fields):
    """Write one structured JSON log line. `event` should be one of
    EVENT_TYPES (a warning is logged, not raised, for anything else — logging
    must never be able to crash the request path)."""
    if event not in EVENT_TYPES:
        logger.warning(json.dumps({"event": "unknown_event_type", "attempted_event": event}))
    record = {"event": event, "ts": time.time(), **fields}
    try:
        logger.info(json.dumps(record, default=str))
    except Exception:  # pragma: no cover
        logger.info(str(record))
    return record
