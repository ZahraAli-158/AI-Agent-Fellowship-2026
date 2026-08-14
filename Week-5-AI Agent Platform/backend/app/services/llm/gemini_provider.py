from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.llm.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    name = "gemini"

    def generate(self, messages: list[dict[str, str]], temperature: float = 0.7,
                 max_tokens: int = 1024, system_prompt: Optional[str] = None) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")

        try:
            import google.generativeai as genai
        except ImportError as e:
            raise RuntimeError(
                "google-generativeai package not installed. Run: "
                "pip install google-generativeai --break-system-packages"
            ) from e

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_prompt or None,
        )

        history = [{"role": m["role"] if m["role"] != "assistant" else "model",
                     "parts": [m["content"]]} for m in messages[:-1]]
        chat = model.start_chat(history=history)
        last_user_msg = messages[-1]["content"] if messages else ""

        result = chat.send_message(
            last_user_msg,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )

        usage = getattr(result, "usage_metadata", None)
        return LLMResponse(
            text=result.text,
            model=self.model,
            provider=self.name,
            input_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
            raw={"finish_reason": getattr(result.candidates[0], "finish_reason", None)}
            if getattr(result, "candidates", None) else None,
        )
