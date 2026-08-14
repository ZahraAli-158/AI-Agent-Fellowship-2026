from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import assistants, auth, conversations, dashboard, documents, export, memory, prompts, skills, voice, workspaces
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import init_db

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

# --- Security: rate limiting (Security Review requirement) ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Baseline security headers (Security Review requirement)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "default_model": settings.DEFAULT_MODEL}


app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(assistants.router)
app.include_router(conversations.router)
app.include_router(documents.router)
app.include_router(memory.router)
app.include_router(prompts.router)
app.include_router(skills.router)
app.include_router(dashboard.router)
app.include_router(export.router)
app.include_router(voice.router)
