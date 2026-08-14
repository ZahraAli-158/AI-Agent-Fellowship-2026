"""
Centralized application configuration.

Root cause of the classic "always mock-gpt" bug this project is designed to avoid:
  - Settings were often instantiated at import time with cached/stale values,
    or DEFAULT_MODEL was read in one place while the provider factory read
    a different (hardcoded) value elsewhere.
  - Fix: single Settings source of truth (this file), loaded once via
    get_settings() (lru_cache), and the LLM provider factory below reads
    ONLY from this Settings object -- never a hardcoded string.
"""
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "AI Workspace Platform"
    ENV: str = Field(default="development")
    DEBUG: bool = True

    # --- Security ---
    SECRET_KEY: str = Field(default="CHANGE_ME_IN_PRODUCTION")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # --- Database ---
    DATABASE_URL: str = Field(default="sqlite:///./ai_workspace.db")

    # --- LLM Providers ---
    DEFAULT_MODEL: str = Field(default="gemini-2.5-flash")

    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: Optional[str] = "http://localhost:11434"

    # --- Vector store ---
    VECTOR_STORE_PATH: str = "./vector_store"
    EMBEDDING_MODEL: str = "text-embedding-004"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120

    # --- Uploads ---
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 20


@lru_cache
def get_settings() -> Settings:
    """Single cached Settings instance. Always import this, never `Settings()` directly."""
    return Settings()
