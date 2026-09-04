"""
Graceful degradation (Week 6, Requirement 20).

Central place documenting + implementing the platform's fallback behavior
for the three most likely failure modes. See docs/WEEK6_REPORT.md section
"Graceful Degradation" for the narrative version of each scenario.
"""
import logging

logger = logging.getLogger("ai_platform.reliability")

VECTOR_DB_DOWN_MESSAGE = ("Knowledge search is temporarily unavailable, so this answer is based on "
                            "general knowledge only and may be missing information from your uploaded "
                            "documents. Please try again shortly.")

FALLBACK_MODEL = "gemini-flash-latest"  # cheaper/older model used if the primary model call fails


def safe_retrieval(retrieval_fn, *args, **kwargs):
    """Scenario 1: Vector DB / embedding service failure.
    Returns (chunks, degraded: bool, message: str|None)."""
    try:
        return retrieval_fn(*args, **kwargs), False, None
    except Exception as exc:
        logger.warning("Retrieval failed, degrading gracefully: %s", exc)
        return [], True, VECTOR_DB_DOWN_MESSAGE


def safe_model_call(primary_fn, fallback_fn, *args, **kwargs):
    """Scenario 2: Primary model failure -> retry against a fallback model.
    Returns (result, used_fallback: bool)."""
    try:
        return primary_fn(*args, **kwargs), False
    except Exception as exc:
        logger.warning("Primary model call failed, using fallback model: %s", exc)
        return fallback_fn(*args, **kwargs), True


def safe_tool_call(tool_fn, *args, **kwargs):
    """Scenario 3: Tool failure -> return a partial result instead of
    crashing the whole agent turn."""
    try:
        return {"status": "ok", "result": tool_fn(*args, **kwargs), "partial": False}
    except Exception as exc:
        logger.warning("Tool call failed, returning partial result: %s", exc)
        return {"status": "failed", "result": None, "partial": True,
                "message": f"This step could not be completed ({exc}); the rest of the "
                            f"request was still processed."}
