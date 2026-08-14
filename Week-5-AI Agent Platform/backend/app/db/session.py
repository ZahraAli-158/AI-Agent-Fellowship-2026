from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Import all models before calling this so they
    register on Base.metadata."""
    import app.models.user  # noqa
    import app.models.workspace  # noqa
    import app.models.workspace_member  # noqa
    import app.models.assistant  # noqa
    import app.models.conversation  # noqa
    import app.models.message  # noqa
    import app.models.document  # noqa
    import app.models.chunk  # noqa
    import app.models.prompt_template  # noqa
    import app.models.skill  # noqa
    import app.models.memory  # noqa
    import app.models.usage_log  # noqa

    Base.metadata.create_all(bind=engine)
