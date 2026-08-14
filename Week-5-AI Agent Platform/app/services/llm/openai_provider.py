from __future__ import annotations

from typing import Any, Optional

from app.services.llm.base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def generate(self, messages: list[dict[str, str]], temperature: float = 0.7,
                 max_tokens: int = 1024, system_prompt: Optional[str] = None) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")

        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "openai package not installed. Run: pip install openai --break-system-packages"
            ) from e

        client = OpenAI(api_key=self.api_key)
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        resp = client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = resp.choices[0]
        usage = resp.usage
        return LLMResponse(
            text=choice.message.content or "",
            model=self.model,
            provider=self.name,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            raw={"finish_reason": choice.finish_reason},
        )
