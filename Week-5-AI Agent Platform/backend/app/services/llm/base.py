from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Optional[dict[str, Any]] = field(default=None, repr=False)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class BaseLLMProvider(ABC):
    """Every concrete provider must implement generate(). Providers must NEVER
    silently swallow auth/config errors and fall back to mock text themselves --
    that decision belongs solely to the ProviderFactory, so the dashboard/logs
    can accurately report which provider actually ran."""

    name: str = "base"

    def __init__(self, model: str, api_key: Optional[str] = None, **kwargs: Any) -> None:
        self.model = model
        self.api_key = api_key
        self.extra = kwargs

    @abstractmethod
    def generate(self, messages: list[dict[str, str]], temperature: float = 0.7,
                 max_tokens: int = 1024, system_prompt: Optional[str] = None) -> LLMResponse:
        ...

    def is_configured(self) -> bool:
        return bool(self.api_key)
