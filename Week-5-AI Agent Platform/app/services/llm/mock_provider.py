from __future__ import annotations

from typing import Optional

from app.services.llm.base import BaseLLMProvider, LLMResponse


class MockLLMProvider(BaseLLMProvider):
    """Deterministic offline provider. Used ONLY when:
      1. No real provider matches the model name, OR
      2. The matched provider has no API key configured, OR
      3. explicit ?force_mock=true is passed (useful for tests).
    It must never be the silent default when a real key exists -- that was
    the original bug."""

    name = "mock"

    def generate(self, messages: list[dict[str, str]], temperature: float = 0.7,
                 max_tokens: int = 1024, system_prompt: Optional[str] = None) -> LLMResponse:
        last = messages[-1]["content"] if messages else ""
        text = (
            "This is a local mock response — no external LLM API key is configured "
            f"for model '{self.model}'. Echoing input: {last[:200]}"
        )
        return LLMResponse(text=text, model="mock-gpt", provider=self.name,
                            input_tokens=len(last.split()), output_tokens=len(text.split()))
