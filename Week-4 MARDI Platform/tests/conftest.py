"""
Pytest session-wide setup.

CRITICAL: this must set LLM_MODE BEFORE any `app.*` module is imported.
`app/services/llm_client.py` creates a module-level singleton
(`llm_client = LLMClient()`) whose mode is resolved ONCE at import time
from `app.config.settings`, which in turn reads `os.getenv(...)` as
dataclass field defaults evaluated once when `app/config.py` is first
imported. If a real API key is present in `.env` (as it will be for
anyone running this project live), leaving LLM_MODE unset makes the
ENTIRE test session silently make real, non-deterministic network calls
instead of using the deterministic mock — which is exactly what caused
`test_full_workflow_end_to_end_in_mock_mode` and other tests to fail with
a real (and non-deterministic) Gemini response instead of the expected
mock response.

pytest imports conftest.py before collecting/importing any test module,
so setting the environment variable here — at module level, not inside a
fixture — reliably runs before that first import, regardless of what the
shell environment or .env file contains.
"""
import os

os.environ["LLM_MODE"] = "mock"
