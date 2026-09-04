"""
Retry strategy (Week 6, Requirement 17).

Do NOT blindly retry every error — only errors classified as retryable.
"""
import time
import random
import logging

logger = logging.getLogger("ai_platform.reliability")

RETRYABLE_EXCEPTIONS = (TimeoutError, ConnectionError)

NON_RETRYABLE_MARKERS = ("invalid argument", "unauthorized", "permission denied",
                          "missing required", "validation error")


class RetryExhausted(Exception):
    pass


def is_retryable(exc: Exception) -> bool:
    if isinstance(exc, RETRYABLE_EXCEPTIONS):
        return True
    msg = str(exc).lower()
    if any(marker in msg for marker in NON_RETRYABLE_MARKERS):
        return False
    # Rate limit / temporary API errors commonly surface as generic
    # exceptions with these words in the message.
    if any(w in msg for w in ("rate limit", "timeout", "temporarily unavailable", "503", "429")):
        return True
    return False


def call_with_retry(fn, *args, max_retries=3, base_delay=0.5, backoff="exponential",
                     jitter=True, on_retry=None, **kwargs):
    """Calls fn(*args, **kwargs), retrying only retryable failures.

    backoff: "exponential" or "fixed".
    on_retry(attempt, exc, delay): optional callback, e.g. to log a
    'retry_attempted' structured log event or record a TraceStep.
    """
    attempt = 0
    last_exc = None
    while attempt <= max_retries:
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - intentionally broad, classified below
            last_exc = exc
            if not is_retryable(exc) or attempt == max_retries:
                raise
            delay = base_delay * (2 ** attempt if backoff == "exponential" else 1)
            if jitter:
                delay += random.uniform(0, base_delay)
            if on_retry:
                on_retry(attempt + 1, exc, delay)
            logger.warning("Retrying after retryable error (attempt %d/%d): %s",
                            attempt + 1, max_retries, exc)
            time.sleep(delay)
            attempt += 1
    raise RetryExhausted(f"Exhausted {max_retries} retries") from last_exc
