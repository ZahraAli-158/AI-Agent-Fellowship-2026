import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))

INSTANCE_DIR = os.path.join(basedir, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)
DEFAULT_DB_PATH = os.path.join(INSTANCE_DIR, "platform.db").replace("\\", "/")


def _normalize_sqlite_url(url: str) -> str:
    """Guarantee any sqlite:/// URL resolves to an ABSOLUTE, forward-slash
    path before Flask-SQLAlchemy ever sees it.

    Why this is necessary: Flask-SQLAlchemy 3.x silently rewrites any
    *relative* sqlite path by joining it onto app.instance_path — so
    "sqlite:///instance/platform.db" does NOT resolve to
    "<project>/instance/platform.db" as you'd expect. It resolves to
    "<project>/instance/instance/platform.db" (instance_path + the literal
    "instance/..." from the URL), a folder that never gets created, which
    is exactly what produces "sqlite3.OperationalError: unable to open
    database file". Forcing an absolute path here sidesteps that rewrite
    entirely, regardless of what a person puts in their own .env file.
    """
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url  # not sqlite (e.g. postgres://...) — leave untouched

    db_path = url[len(prefix):]
    if db_path in ("", ":memory:"):
        return url  # in-memory DB — nothing to resolve

    if not os.path.isabs(db_path):
        db_path = os.path.join(basedir, db_path)

    db_path = db_path.replace("\\", "/")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return prefix + db_path


_raw_database_url = os.environ.get("DATABASE_URL", "sqlite:///" + DEFAULT_DB_PATH)


class Config:
    """Central application configuration, loaded from environment variables."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = _normalize_sqlite_url(_raw_database_url)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_CHAT_MODEL = os.environ.get("GEMINI_CHAT_MODEL", "gemini-3.6-flash")
    GEMINI_EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")

    # Optional — enables the Meeting Agent's "email me my tasks" tool via
    # Gmail SMTP. Use a Gmail App Password, not the account's login
    # password (see app/services/email_service.py for setup steps).
    GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
    GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB

    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

    CHUNK_SIZE = 800          # characters per chunk
    CHUNK_OVERLAP = 120       # overlap between chunks

    # Rough per-1K-token cost estimates (USD) used for the cost dashboard.
    # These are placeholders for demonstration / experimentation purposes.
    COST_PER_1K_INPUT_TOKENS = 0.000075
    COST_PER_1K_OUTPUT_TOKENS = 0.0003
