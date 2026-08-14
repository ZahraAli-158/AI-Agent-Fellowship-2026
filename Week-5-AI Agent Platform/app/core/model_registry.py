"""
Maps a model name (e.g. from DEFAULT_MODEL or an Assistant's `model` field)
to the provider that serves it. This is the piece that was missing in the
buggy version described in the spec: workspaces/assistants stored a model
string, but the chat service never consulted it -- it always built
MockLLMProvider directly. Fix: chat_service -> provider_factory ->
model_registry -> concrete provider, every time, no shortcuts.
"""
from __future__ import annotations

PROVIDER_PREFIXES: dict[str, str] = {
    "gemini": "gemini",
    "gpt": "openai",
    "o1": "openai",
    "o3": "openai",
    "claude": "anthropic",
    "llama": "ollama",
    "mistral": "ollama",
    "qwen": "ollama",
}


def resolve_provider_name(model: str) -> str:
    """Return the provider key ('gemini' | 'openai' | 'anthropic' | 'ollama' | 'mock')
    for a given model string. Falls back to 'mock' only if nothing matches."""
    if not model:
        return "mock"
    lower = model.lower()
    for prefix, provider in PROVIDER_PREFIXES.items():
        if lower.startswith(prefix):
            return provider
    return "mock"
