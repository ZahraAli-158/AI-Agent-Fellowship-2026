"""
Thin LLM client wrapper.

Two modes:
  - "live": calls a real hosted LLM (Anthropic Claude OR Google Gemini,
    selected via LLM_PROVIDER — the assignment does not mandate a specific
    LLM provider, only the orchestration framework, so this is swappable).
  - "mock": no network call at all. Each agent supplies a `mock_fn` that
    deterministically builds the response it would expect back. This keeps
    the graph, routing, revision loop, and parallel fan-out fully
    exercisable and testable without any API key or network access —
    useful for CI, grading, and offline demos.

This is also where Model API Failure handling (Requirement 14) lives: any
live call is wrapped in a retry-once policy, surfaced to the caller as a
structured error rather than a raw exception.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import Callable, Optional

from app.config import settings
from app.observability.logging_config import get_logger

logger = get_logger(__name__)

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None

try:
    from google import genai as google_genai
except ImportError:  # pragma: no cover
    google_genai = None

# A small dedicated pool just for bounding LLM calls with a hard wall-clock
# timeout. Neither the anthropic nor google-genai SDKs are guaranteed to
# honor a timeout on every code path (proxies, DNS stalls, SDK internals),
# so instead of trusting the SDK's own timeout handling, the call itself is
# run in a worker thread and given a hard deadline here. If the deadline is
# exceeded, `future.result(timeout=...)` raises `FutureTimeoutError` even
# though the underlying network call may still be silently stuck — this is
# what turns an indefinite hang into a bounded, catchable failure.
_LLM_CALL_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm-call")


def _call_with_timeout(fn: Callable[[], str], timeout_s: int) -> str:
    future = _LLM_CALL_POOL.submit(fn)
    try:
        return future.result(timeout=timeout_s)
    except FutureTimeoutError as exc:
        raise TimeoutError(f"LLM call did not return within {timeout_s}s") from exc


@dataclass
class LLMResult:
    text: str
    mode: str
    error: Optional[str] = None


def _strip_code_fences(text: str) -> str:
    """Some providers wrap JSON in ```json ... ``` even when asked not to.
    Strips that so downstream json.loads() calls in the agents don't break.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines)
    return stripped.strip()


class LLMClient:
    def __init__(self) -> None:
        self.mode = settings.resolved_llm_mode()
        self.provider = settings.llm_provider
        self._client = None
        if self.mode == "live":
            if self.provider == "gemini":
                if google_genai is None:
                    raise RuntimeError("google-genai package not installed but LLM_PROVIDER=gemini")
                self._client = google_genai.Client(api_key=settings.gemini_api_key)
            else:
                if anthropic is None:
                    raise RuntimeError("anthropic package not installed but LLM_PROVIDER=anthropic")
                self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def complete(
        self,
        system: str,
        user: str,
        mock_fn: Optional[Callable[[], str]] = None,
        max_tokens: int = 1200,
    ) -> LLMResult:
        if self.mode == "mock":
            if mock_fn is None:
                raise ValueError("mock_fn is required when running in mock LLM mode")
            return LLMResult(text=mock_fn(), mode="mock")

        # live mode, with a single retry per Requirement 14 (Model API Failure)
        last_error = None
        for attempt in range(settings.tool_max_retries + 1):
            try:
                if self.provider == "gemini":
                    text = _call_with_timeout(lambda: self._call_gemini(system, user, max_tokens), settings.llm_timeout_s)
                else:
                    text = _call_with_timeout(lambda: self._call_anthropic(system, user, max_tokens), settings.llm_timeout_s)
                return LLMResult(text=_strip_code_fences(text), mode="live")
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                logger.warning("live call attempt %d failed: %s", attempt + 1, last_error)
        return LLMResult(text="", mode="live", error=last_error)

    def _call_anthropic(self, system: str, user: str, max_tokens: int) -> str:
        response = self._client.messages.create(
            model=settings.model_name,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if getattr(block, "type", "") == "text")

    def _call_gemini(self, system: str, user: str, max_tokens: int) -> str:
        response = self._client.models.generate_content(
            model=settings.gemini_model_name,
            contents=user,
            config={
                "system_instruction": system,
                "max_output_tokens": max_tokens,
                "response_mime_type": "application/json",
            },
        )
        return response.text


llm_client = LLMClient()

