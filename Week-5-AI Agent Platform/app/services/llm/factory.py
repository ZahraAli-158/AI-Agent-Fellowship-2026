"""
LLM Provider Factory.

THE BUG (as described in the spec) and its root cause:
  The chat service was instantiating `MockLLMProvider()` directly with no
  arguments, regardless of what the workspace/assistant's `model` field or
  DEFAULT_MODEL said. So even with a valid GEMINI_API_KEY and
  DEFAULT_MODEL=gemini-2.5-flash in .env, chat always returned mock text and
  the dashboard always showed "mock-gpt" (a hardcoded literal, not derived
  from any real provider response).

THE FIX:
  1. Every call site MUST go through get_provider(model=...) below -- never
     instantiate a provider class directly elsewhere in the codebase.
  2. model defaults to settings.DEFAULT_MODEL when the caller doesn't pass
     one explicitly (e.g. a brand-new Assistant that hasn't overridden it).
  3. The provider is chosen by resolve_provider_name(model), then we check
     if that provider actually has a configured API key. Only if it's
     unconfigured (or truly unknown) do we fall back to MockLLMProvider --
     and the returned LLMResponse.model still reflects what was *requested*
     so the dashboard can show "gemini-2.5-flash (fallback: mock)" instead
     of silently lying.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.core.config import Settings, get_settings
from app.core.model_registry import resolve_provider_name
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import BaseLLMProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.mock_provider import MockLLMProvider
from app.services.llm.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

_PROVIDER_CLASSES: dict[str, type[BaseLLMProvider]] = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "mock": MockLLMProvider,
}


def _api_key_for(provider_name: str, settings: Settings) -> Optional[str]:
    return {
        "gemini": settings.GEMINI_API_KEY,
        "openai": settings.OPENAI_API_KEY,
        "anthropic": settings.ANTHROPIC_API_KEY,
    }.get(provider_name)


def get_provider(model: Optional[str] = None, settings: Optional[Settings] = None) -> BaseLLMProvider:
    """Resolve the correct provider for a given model name (or DEFAULT_MODEL).
    This is the ONLY sanctioned way to obtain an LLM provider in this codebase."""
    settings = settings or get_settings()
    resolved_model = model or settings.DEFAULT_MODEL

    provider_name = resolve_provider_name(resolved_model)
    api_key = _api_key_for(provider_name, settings)

    if provider_name == "mock" or not api_key:
        if provider_name != "mock":
            logger.warning(
                "Requested model '%s' resolves to provider '%s' but no API key is "
                "configured; falling back to MockLLMProvider.",
                resolved_model, provider_name,
            )
        return MockLLMProvider(model=resolved_model)

    provider_cls = _PROVIDER_CLASSES[provider_name]
    return provider_cls(model=resolved_model, api_key=api_key)
