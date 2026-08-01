"""
Central logging configuration.

`app/config.py` has always exposed a `LOG_LEVEL` environment variable, but
nothing previously read it — every module used bare `print()` calls for
operational messages instead of Python's standard `logging` module. This
module is the single place that wires `settings.log_level` into a real
logging configuration, so:

  - Every module gets a properly-named logger via `logging.getLogger(__name__)`,
    making the source of each message traceable (e.g. `app.api`,
    `app.services.llm_client`).
  - Verbosity is controlled by the existing `LOG_LEVEL` env var (already
    documented in `.env.example` and `README.md`) instead of being fixed.
  - Configuration happens exactly once per process, regardless of how many
    times an entry point (CLI, FastAPI app, tests) calls it.

This intentionally does NOT touch the CLI's own user-facing output in
`app/main.py` (the run banner, final report text, etc.) or the interactive
prompts in `app/graph/human.py::cli_callback` — those are the program's
actual designed output/interaction surface for a human running the CLI,
not diagnostic/operational logging, and remain plain `print()` calls.
"""
from __future__ import annotations

import logging

from app.config import settings

_configured = False


def configure_logging() -> None:
    """Idempotently configures the root logger from `settings.log_level`.

    Safe to call from multiple entry points (`app/main.py`, `app/api.py`,
    test setup) — only the first call actually installs a handler.
    """
    global _configured
    if _configured:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper so callers don't need a separate `logging`
    import alongside this module — ensures configuration has happened
    before handing back the logger."""
    configure_logging()
    return logging.getLogger(name)
