"""
Environment-based configuration. No secrets are hard-coded here — everything
sensitive is read from environment variables (see .env.example).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # LLM provider: "anthropic" | "gemini"
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")

    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    model_name: str = os.getenv("MODEL_NAME", "claude-sonnet-5")

    # Gemini
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model_name: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

    # When no API key is configured (e.g. local dev, CI, grading without
    # secrets), agents fall back to a deterministic mock LLM so the graph
    # is still fully exercisable end-to-end.
    llm_mode: str = os.getenv("LLM_MODE", "auto")  # "auto" | "mock" | "live"

    # Hard wall-clock cap (seconds) on a single live LLM call. Without this,
    # a stalled network connection or a hung SDK client blocks the entire
    # background workflow thread forever with no exception raised — the
    # workflow silently never progresses past its initial "pending" state.
    llm_timeout_s: int = int(os.getenv("LLM_TIMEOUT_S", "30"))

    # Workflow controls
    max_revisions: int = int(os.getenv("MAX_REVISIONS", "2"))
    tool_max_retries: int = int(os.getenv("TOOL_MAX_RETRIES", "1"))
    research_corpus_path: str = os.getenv(
        "RESEARCH_CORPUS_PATH", os.path.join(os.path.dirname(__file__), "storage", "corpus")
    )

    # Human-in-the-loop
    auto_approve_checkpoints: bool = _bool_env("AUTO_APPROVE_CHECKPOINTS", False)

    # Observability
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    trace_dir: str = os.getenv("TRACE_DIR", os.path.join(os.path.dirname(__file__), "..", "traces"))

    def resolved_llm_mode(self) -> str:
        if self.llm_mode in {"mock", "live"}:
            return self.llm_mode
        active_key = self.gemini_api_key if self.llm_provider == "gemini" else self.anthropic_api_key
        return "live" if active_key else "mock"


settings = Settings()
