from __future__ import annotations

from typing import Any, Optional

from app.services.llm.base import BaseLLMProvider, LLMResponse


class AnthropicProvider(BaseLLMProvider):
    name = "anthropic"

    def generate(self, messages: list[dict[str, str]], temperature: float = 0.7,
                 max_tokens: int = 1024, system_prompt: Optional[str] = None) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")

        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError(
                "anthropic package not installed. Run: pip install anthropic --break-system-packages"
            ) from e

        client = anthropic.Anthropic(api_key=self.api_key)
        resp = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=messages,
        )
        text = "".join(block.text for block in resp.content if hasattr(block, "text"))
        return LLMResponse(
            text=text,
            model=self.model,
            provider=self.name,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            raw={"stop_reason": resp.stop_reason},
        )
